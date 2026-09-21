"""stock.naver.com/market/stock/kr 에서 코스피200 지수 데이터를 크롤링한다. (Selenium + BeautifulSoup4)

이 페이지는 JavaScript로 화면을 그리므로 requests 만으로는 지수 카드가 HTML에 없다.
1) Selenium(헤드리스 Chrome)으로 화면을 완성시킨 뒤
2) 완성된 HTML을 BeautifulSoup으로 파싱한다.

파싱 기준이 되는 태그 (CSS 클래스 뒤의 해시 `__q_CU3` 등은 배포 때마다 바뀌므로
`[class*="접두사"]` 로 접두사만 비교한다):
    a[data-nlogs="home.nixkospi200"]                      코스피200 지수 카드
      [class*="MarketStockInfo_stock-name"]               지수명
      [class*="ModulePriceNumber_price"]                  현재값
      [class*="ModulePriceChange_module-price-change"]    상승/하락 방향 (클래스에 rise / fall)
        [class*="ModulePriceChange_amount"]               전일 대비 (안의 .a11y 는 "상승"/"하락" 문구)
      [class*="ModulePercent_module-percent"]             등락률
      [class*="MarketStockInfo_stock-info__"] > span      "52주 최고" / 값

구성종목 200개는 m.stock.naver.com/domestic/index/KPI200/enrollstocks 에서 가져온다.
이 화면은 한 번에 50개만 보여주고 [더보기] 버튼을 눌러야 다음 50개가 붙는 "더보기 페이징"이라,
Selenium 이 버튼이 없어질 때까지 눌러 전부 펼친 뒤 BeautifulSoup 으로 파싱한다.
    ProductDataListItem_item__       종목 한 줄 (이 접두사로 전체 항목을 찾음)
    ProductDataListItem_name         종목명      ProductDataListItem_sub-info   종목코드
    ProductDataListItem_price__      현재가      RegularOrCloseMarketPrice_rate 전일비 / (등락률)
    RegularOrCloseMarketPrice_RISING / _FALLING  상승/하락 방향
    ProductDataListItem_total__      거래량·시가총액   ProductDataListItem_amount__  거래대금

사용법:
    python kospi200_soup.py                  # 지수 요약 + 구성종목 전체 -> JSON/CSV 저장
    python kospi200_soup.py -n 20            # 화면에는 상위 20개만 표시 (저장은 전체)
    python kospi200_soup.py --index-only     # 코스피200 지수 카드만
    python kospi200_soup.py --all            # (지수 카드) 코스피/코스닥/선물/환율 등 전체 카드
    python kospi200_soup.py --html page.html # 저장해 둔 HTML 의 지수 카드를 파싱 (브라우저 불필요)
    python kospi200_soup.py --save-html p.html  # 화면이 완성된 HTML 도 파일로 저장

필요 패키지: pip install selenium beautifulsoup4   (Chrome 또는 Edge 필요)
"""
import argparse
import csv
import json
import re
import sys
import time

from bs4 import BeautifulSoup

URL = "https://stock.naver.com/market/stock/kr"
KOSPI200_KEY = "home.nixkospi200"
CARD_SELECTOR = 'a[data-nlogs^="home.nix"]'   # 지수/환율/원자재 카드 링크
BASE = "https://stock.naver.com"


# ---------------------------------------------------------------- 브라우저
def render_page(url, timeout=20, browser="chrome"):
    """Selenium 으로 페이지를 열고 코스피200 카드가 나타날 때까지 기다린 뒤 HTML 을 반환."""
    from selenium import webdriver
    from selenium.webdriver.support.ui import WebDriverWait

    if browser == "edge":
        opts = webdriver.EdgeOptions()
        make = webdriver.Edge
    else:
        opts = webdriver.ChromeOptions()
        make = webdriver.Chrome
    for arg in ("--headless=new", "--disable-gpu", "--window-size=1400,1000",
                "--lang=ko-KR", "--log-level=3"):
        opts.add_argument(arg)
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])

    driver = make(options=opts)
    try:
        driver.get(url)
        card = f'a[data-nlogs="{KOSPI200_KEY}"] [class*="ModulePriceNumber_price"]'
        # 카드가 생기고 가격 글자가 채워질 때까지 대기
        WebDriverWait(driver, timeout).until(
            lambda d: any(e.text.strip() for e in d.find_elements("css selector", card))
        )
        return driver.page_source
    finally:
        driver.quit()


# ---------------------------------------------------------------- 파싱
def to_number(text):
    """'1,112.16' / '(+2.01%)' / '-30,206' -> 숫자, 못 읽으면 None."""
    if text is None:
        return None
    m = re.search(r"[-+]?\d[\d,]*\.?\d*", str(text))
    if not m:
        return None
    s = m.group().replace(",", "")
    return float(s) if "." in s else int(s)


def text_of(node, selector):
    el = node.select_one(selector)
    return el.get_text(strip=True) if el else ""


def parse_card(card):
    """지수 카드 <a> 하나를 dict 로 변환. (작은 카드/큰 카드 공통)"""
    name = text_of(card, '[class*="MarketStockInfo_stock-name"]') or \
        text_of(card, '[class*="HomeIndicatorsKr_stock-name"]')

    # 방향: 변화량 영역의 클래스(rise/fall) 와 화면낭독용 문구(.a11y: 상승/하락)
    change_box = card.select_one('[class*="ModulePriceChange_module-price-change"]')
    direction = ""
    if change_box:
        classes = " ".join(change_box.get("class", []))
        a11y = change_box.select_one(".a11y")
        direction = a11y.get_text(strip=True) if a11y else ""
        if not direction:
            direction = "상승" if "_rise" in classes else "하락" if "_fall" in classes else "보합"

    amount_el = card.select_one('[class*="ModulePriceChange_amount"]')
    if amount_el:
        for a11y in amount_el.select(".a11y"):
            a11y.extract()          # "상승"/"하락" 문구가 숫자에 섞이지 않게 제거
        change = to_number(amount_el.get_text(strip=True))
    else:
        change = None
    rate = to_number(text_of(card, '[class*="ModulePercent_module-percent"]'))
    sign = -1 if direction == "하락" else 1

    info = {}
    # "stock-info__" 로 끝까지 맞춰야 바깥 래퍼("stock-info-item__")가 섞이지 않는다
    for box in card.select('[class*="MarketStockInfo_stock-info__"]'):
        spans = box.find_all("span")
        if len(spans) >= 2 and spans[0].get_text(strip=True):
            info[spans[0].get_text(strip=True)] = to_number(spans[1].get_text(strip=True))

    # 큰 카드(코스피/코스닥)에만 있는 투자자 동향·등락 종목 수
    trend = {}
    for item in card.select('[class*="HomeIndicatorsKr_index-trend-item"]'):
        title = text_of(item, '[class*="HomeIndicatorsKr_item-title"]')
        value = text_of(item, '[class*="HomeIndicatorsKr_item-value"]')
        if title:
            trend[title] = value

    href = card.get("href", "")
    return {
        "key": card.get("data-nlogs", ""),
        "name": name,
        "price": to_number(text_of(card, '[class*="ModulePriceNumber_price"]')),
        "change": None if change is None else sign * change,
        "rate": None if rate is None else sign * abs(rate),
        "direction": direction or "-",
        "market_status": text_of(card, '[class*="ModuleMarketStatus_text"]'),
        "extra": info,
        "trend": trend,
        "url": BASE + href if href.startswith("/") else href,
    }


def parse_indicators(html):
    soup = BeautifulSoup(html, "html.parser")
    return [parse_card(a) for a in soup.select(CARD_SELECTOR)]


# ---------------------------------------------------------------- 출력
def fmt(card):
    price = "-" if card["price"] is None else f"{card['price']:,}"
    change = "-" if card["change"] is None else f"{card['change']:+,}"
    rate = "-" if card["rate"] is None else f"{card['rate']:+.2f}%"
    line = f"{card['name']:<12} {price:>10}  {change:>9}  {rate:>8}  {card['direction']}"
    if card["market_status"]:
        line += f"  [{card['market_status']}]"
    for k, v in card["extra"].items():
        line += f"  {k} {v:,}" if v is not None else ""
    return line


# ---------------------------------------------------------------- 구성종목 (더보기 페이징)
STOCKS_URL = "https://m.stock.naver.com/domestic/index/KPI200/enrollstocks"
ITEM_SEL = '[class*="ProductDataListItem_item__"]'
MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Mobile/15E148")
MORE_XPATH = "//button[contains(normalize-space(.), '더보기')]"


def make_driver(browser="chrome", mobile=False):
    from selenium import webdriver
    if browser == "edge":
        opts, make = webdriver.EdgeOptions(), webdriver.Edge
    else:
        opts, make = webdriver.ChromeOptions(), webdriver.Chrome
    args = ["--headless=new", "--disable-gpu", "--lang=ko-KR", "--log-level=3",
            "--window-size=500,1000" if mobile else "--window-size=1400,1000"]
    if mobile:
        args.append(f"--user-agent={MOBILE_UA}")
    for a in args:
        opts.add_argument(a)
    opts.add_experimental_option("excludeSwitches", ["enable-logging"])
    return make(options=opts)


def render_all_stocks(browser="chrome", timeout=15, max_pages=20, log=print):
    """[더보기] 를 끝까지 눌러 구성종목 전체가 펼쳐진 HTML 을 반환한다."""
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait

    driver = make_driver(browser, mobile=True)
    try:
        driver.get(STOCKS_URL)
        count = lambda: len(driver.find_elements(By.CSS_SELECTOR, ITEM_SEL))
        WebDriverWait(driver, timeout).until(lambda d: count() > 0)
        log(f"  1페이지: {count()}개")

        for page in range(2, max_pages + 1):
            buttons = driver.find_elements(By.XPATH, MORE_XPATH)
            if not buttons:
                break                       # 더보기 버튼이 없으면 마지막 페이지
            before = count()
            driver.execute_script("arguments[0].scrollIntoView({block:'center'})", buttons[0])
            driver.execute_script("arguments[0].click()", buttons[0])
            try:
                WebDriverWait(driver, timeout).until(lambda d: count() > before)
            except TimeoutException:
                log("  새 항목이 늘지 않아 중단합니다.")
                break
            log(f"  {page}페이지: {count()}개")
            time.sleep(0.5)                 # 서버에 부담을 주지 않도록 간격을 둔다
        return driver.page_source
    finally:
        driver.quit()


_KOR_UNITS = {"만": 10**4, "억": 10**8, "조": 10**12}


def kor_number(text):
    """'8조 6,048억' -> 8_604_800_000_000, '3,171만' -> 31_710_000, '274,000' -> 274000."""
    text = (text or "").strip()
    if not text:
        return None
    total, found = 0, False
    # "6천억" = 6 x 천(1,000) x 억 / "482억 700만" 처럼 단위가 이어지는 표기를 모두 처리
    for num, thousand, unit in re.findall(r"([\d,.]+)\s*(천?)\s*([만억조]?)", text):
        num = num.replace(",", "")
        if not num or num == ".":
            continue
        found = True
        total += float(num) * (1000 if thousand else 1) * _KOR_UNITS.get(unit, 1)
    return int(total) if found else None


def parse_stock_item(item):
    """종목 한 줄(<div class=ProductDataListItem_item__...>) -> dict."""
    rates = [r.get_text(strip=True) for r in item.select('[class*="RegularOrCloseMarketPrice_rate"]')]
    article = item.select_one('[class*="RegularOrCloseMarketPrice_article"]')
    cls = " ".join(article.get("class", [])) if article else ""
    sign = -1 if ("FALLING" in cls or "LOWER" in cls) else 1
    change = to_number(rates[0]) if rates else None
    rate = to_number(rates[1]) if len(rates) > 1 else None

    link = item.select_one('a[class*="ProductDataListItem_link"]')
    href = link.get("href", "") if link else ""
    rank = link.get("data-nlog-click-rank", "") if link else ""
    cap = item.select_one('[class*="ProductDataListItem_stock-market-cap"] [class*="ProductDataListItem_total__"]')
    totals = item.select('[class*="ProductDataListItem_total__"]')   # [거래량, 시가총액]
    volume_el = totals[0] if totals and totals[0] is not cap else None
    amount = text_of(item, '[class*="ProductDataListItem_amount__"]')
    volume_text = volume_el.get_text(strip=True) if volume_el else ""
    cap_text = cap.get_text(strip=True) if cap else ""

    return {
        "rank": int(rank) if rank.isdigit() else None,
        "code": text_of(item, '[class*="ProductDataListItem_sub-info"]'),
        "name": text_of(item, '[class*="ProductDataListItem_name"]'),
        "price": to_number(text_of(item, '[class*="ProductDataListItem_price__"]')),
        "change": None if change is None else sign * abs(change),
        "rate": None if rate is None else sign * abs(rate),
        "volume_text": volume_text,
        "volume": kor_number(volume_text),
        "amount_text": amount,
        "amount_won": kor_number(amount),
        "market_cap_text": cap_text,
        "market_cap_won": kor_number(cap_text),
        "url": ("https://m.stock.naver.com" + href) if href.startswith("/") else href,
    }


def parse_stocks(html):
    soup = BeautifulSoup(html, "html.parser")
    rows, seen = [], set()
    for item in soup.select(ITEM_SEL):
        row = parse_stock_item(item)
        if not row["code"] or row["code"] in seen:   # 중복/빈 항목 방지
            continue
        seen.add(row["code"])
        rows.append(row)
    return rows


STOCK_COLUMNS = ["rank", "code", "name", "price", "change", "rate", "volume", "amount_won",
                 "market_cap_won", "volume_text", "amount_text", "market_cap_text", "url"]


def save_stocks_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:   # BOM: 엑셀에서 한글 깨짐 방지
        w = csv.DictWriter(f, fieldnames=STOCK_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def print_stocks(rows, limit):
    print(f"{'순위':>4} {'코드':<7} {'종목명':<14} {'현재가':>10} {'등락률':>8}  {'거래대금':>12}  {'시가총액':>10}")
    for r in rows[:limit]:
        rate = "-" if r["rate"] is None else f"{r['rate']:+.2f}%"
        price = "-" if r["price"] is None else f"{r['price']:,}"
        print(f"{r['rank'] or '':>4} {r['code']:<7} {r['name']:<14} {price:>10} {rate:>8}  "
              f"{r['amount_text']:>12}  {r['market_cap_text']:>10}")
    if len(rows) > limit:
        print(f"... 외 {len(rows) - limit}개")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(description="코스피200 크롤러 (Selenium + BeautifulSoup4)")
    ap.add_argument("--html", metavar="파일", help="브라우저 대신 저장된 HTML 파일의 지수 카드를 파싱")
    ap.add_argument("--save-html", metavar="파일", help="지수 화면이 완성된 HTML 을 저장")
    ap.add_argument("--all", action="store_true", help="(지수 카드) 코스피200뿐 아니라 모든 카드 출력")
    ap.add_argument("--index-only", action="store_true", help="구성종목은 건너뛰고 지수 카드만")
    ap.add_argument("-n", "--num", type=int, default=10, help="화면에 표시할 종목 수 (기본 10)")
    ap.add_argument("--browser", choices=["chrome", "edge"], default="chrome")
    ap.add_argument("-o", "--out", default="kospi200.json", help="지수 카드 JSON 파일")
    ap.add_argument("--stocks-out", default="kospi200_stocks", metavar="이름",
                    help="구성종목 저장 파일 이름(확장자 제외, .json/.csv 생성)")
    args = ap.parse_args()

    # ---- 1) 지수 카드
    if args.html:
        with open(args.html, encoding="utf-8") as f:
            html = f.read()
    else:
        print(f"[1/2] 지수 페이지 로딩 중: {URL}")
        try:
            html = render_page(URL, browser=args.browser)
        except Exception as e:  # Selenium 예외 종류가 많아 한 번에 처리
            print(f"페이지를 불러오지 못했습니다: {type(e).__name__}: {e}")
            return 1
        if args.save_html:
            with open(args.save_html, "w", encoding="utf-8") as f:
                f.write(html)

    cards = parse_indicators(html)
    if not cards:
        print("지수 카드를 찾지 못했습니다. 페이지 구조가 바뀌었을 수 있습니다.")
        return 1

    picked = cards if args.all else [c for c in cards if c["key"] == KOSPI200_KEY]
    if not picked:
        print("코스피200 카드를 찾지 못했습니다. --all 로 찾은 카드를 확인하세요.")
        return 1

    print()
    for c in picked:
        print(fmt(c))
        for k, v in c["trend"].items():
            print(f"    {k}: {v}")
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(picked, f, ensure_ascii=False, indent=2)
    print(f"\n지수 {len(picked)}건을 {args.out}에 저장했습니다.")

    if args.index_only or args.html:
        return 0

    # ---- 2) 구성종목 전체 (더보기 페이징)
    print(f"\n[2/2] 구성종목 수집 중 ([더보기]를 끝까지 누릅니다): {STOCKS_URL}")
    try:
        stocks_html = render_all_stocks(args.browser)
    except Exception as e:
        print(f"구성종목을 불러오지 못했습니다: {type(e).__name__}: {e}")
        return 1
    rows = parse_stocks(stocks_html)
    if not rows:
        print("구성종목을 찾지 못했습니다. 페이지 구조가 바뀌었을 수 있습니다.")
        return 1

    print(f"\n구성종목 {len(rows)}개 수집 완료\n")
    print_stocks(rows, args.num)
    with open(args.stocks_out + ".json", "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    save_stocks_csv(rows, args.stocks_out + ".csv")
    print(f"\n{len(rows)}개를 {args.stocks_out}.json / {args.stocks_out}.csv에 저장했습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
