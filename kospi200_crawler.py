"""코스피200 지수와 구성종목 데이터를 수집해 CSV/엑셀로 저장한다.

https://stock.naver.com/market/stock/kr 는 브라우저에서 JavaScript로 데이터를 채우는 페이지라
HTML에는 코스피200 데이터가 들어 있지 않다(BeautifulSoup으로 파싱할 표가 없음).
그래서 이 페이지가 내부적으로 호출하는 JSON API(m.stock.naver.com/api/index/KPI200/...)를 사용한다.

사용법:
    python kospi200_crawler.py                 # 화면 출력 + kospi200.csv 저장
    python kospi200_crawler.py -n 20           # 화면에는 상위 20개만 표시
    python kospi200_crawler.py -x              # 엑셀(kospi200.xlsx)로도 저장

필요 패키지: pip install requests   (엑셀 저장 시 openpyxl)
"""
import argparse
import csv
import sys
import time

import requests

BASE = "https://m.stock.naver.com/api/index/KPI200"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://stock.naver.com/",
}
TIMEOUT = 10
PAGE_SIZE = 50   # 서버가 허용하는 최대값 (100 이상은 400 오류)
MAX_PAGES = 10   # 무한 반복 방지

COLUMNS = ["순위", "종목코드", "종목명", "현재가", "전일비", "등락률(%)",
           "거래량", "거래대금(백만원)", "시가총액(억원)", "기준시각", "URL"]


def get_json(path, **params):
    resp = requests.get(f"{BASE}/{path}", params=params, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def to_number(text):
    """'1,234.5' -> 1234.5, 'N/A' 또는 빈 값 -> None."""
    if text is None:
        return None
    s = str(text).replace(",", "").strip()
    try:
        return float(s) if "." in s else int(s)
    except ValueError:
        return None


def signed(value, direction):
    """API는 전일비/등락률을 절댓값으로 주므로 하락이면 음수로 바꾼다."""
    if value is None:
        return None
    return -abs(value) if direction in ("FALLING", "LOWER_LIMIT") else value


def fetch_index_summary():
    """코스피200 지수 현재값 요약."""
    basic = get_json("basic")
    info = {t["key"]: t["value"] for t in get_json("integration").get("totalInfos", [])}
    direction = (basic.get("compareToPreviousPrice") or {}).get("name")
    return {
        "지수명": basic.get("stockName"),
        "현재값": to_number(basic.get("closePrice")),
        "전일비": signed(to_number(basic.get("compareToPreviousClosePrice")), direction),
        "등락률(%)": signed(to_number(basic.get("fluctuationsRatio")), direction),
        "시장상태": basic.get("marketStatus"),
        "기준시각": basic.get("localTradedAt"),
        **{k: info.get(k) for k in ("전일", "시가", "고가", "저가", "거래량", "대금", "52주 최고", "52주 최저")},
    }


def fetch_constituents():
    """코스피200 구성종목 전체(페이지를 넘기며 수집)."""
    rows, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        try:
            items = get_json("enrollStocks", page=page, pageSize=PAGE_SIZE)
        except requests.HTTPError:  # 범위를 넘긴 페이지는 400 등으로 응답
            break
        if not items:
            break
        for it in items:
            code = it.get("itemCode")
            if code in seen:
                continue
            seen.add(code)
            direction = (it.get("compareToPreviousPrice") or {}).get("name")
            rows.append({
                "종목코드": code,
                "종목명": it.get("stockName"),
                "현재가": to_number(it.get("closePrice")),
                "전일비": signed(to_number(it.get("compareToPreviousClosePrice")), direction),
                "등락률(%)": signed(to_number(it.get("fluctuationsRatio")), direction),
                "거래량": to_number(it.get("accumulatedTradingVolume")),
                "거래대금(백만원)": to_number(it.get("accumulatedTradingValue")),
                "시가총액(억원)": to_number(it.get("marketValue")),
                "기준시각": it.get("localTradedAt"),
                "URL": it.get("newPcUrl") or it.get("endUrl"),
            })
        if len(items) < PAGE_SIZE:
            break
        time.sleep(0.3)  # 서버 부담을 줄이기 위한 간격
    # 시가총액 큰 순으로 순위 부여
    rows.sort(key=lambda r: r["시가총액(억원)"] or 0, reverse=True)
    for i, r in enumerate(rows, 1):
        r["순위"] = i
    return rows


def save_csv(rows, path):
    # utf-8-sig: 엑셀에서 열어도 한글이 깨지지 않도록 BOM 포함
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def save_excel(summary, rows, path):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "구성종목"
    ws.append(COLUMNS)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="3B5BDB")
        c.alignment = Alignment(horizontal="center")
    for r in rows:
        ws.append([r.get(c) for c in COLUMNS])
    fmt = {"현재가": "#,##0", "전일비": "#,##0;[Red]-#,##0", "등락률(%)": "0.00;[Red]-0.00",
           "거래량": "#,##0", "거래대금(백만원)": "#,##0", "시가총액(억원)": "#,##0"}
    for idx, name in enumerate(COLUMNS, 1):
        ws.column_dimensions[get_column_letter(idx)].width = 34 if name in ("URL", "기준시각") else 16
        if name in fmt:
            for row in range(2, ws.max_row + 1):
                ws.cell(row=row, column=idx).number_format = fmt[name]
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    s = wb.create_sheet("지수요약")
    for k, v in summary.items():
        s.append([k, v])
    s.column_dimensions["A"].width = 16
    s.column_dimensions["B"].width = 30
    wb.save(path)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(description="코스피200 데이터 크롤러")
    ap.add_argument("-n", "--num", type=int, default=10, help="화면에 표시할 종목 수 (기본 10)")
    ap.add_argument("-o", "--out", default="kospi200.csv", help="저장할 CSV 파일")
    ap.add_argument("-x", "--xlsx", nargs="?", const="kospi200.xlsx", metavar="파일",
                    help="엑셀(.xlsx)로도 저장")
    args = ap.parse_args()

    try:
        summary = fetch_index_summary()
        rows = fetch_constituents()
    except requests.RequestException as e:
        print(f"요청 실패: {e}")
        return 1
    if not rows:
        print("구성종목 데이터를 가져오지 못했습니다. API가 변경되었을 수 있습니다.")
        return 1

    print(f"[{summary['지수명']}] {summary['현재값']:,} "
          f"({summary['전일비']:+,} / {summary['등락률(%)']:+.2f}%)  "
          f"{summary['시장상태']}  {summary['기준시각']}")
    print(f"시가 {summary['시가']} / 고가 {summary['고가']} / 저가 {summary['저가']} / "
          f"52주 {summary['52주 최저']}~{summary['52주 최고']}\n")

    print(f"{'순위':>3} {'코드':<7} {'종목명':<14} {'현재가':>10} {'등락률':>8} {'시가총액(억)':>14}")
    for r in rows[: args.num]:
        rate = r["등락률(%)"]
        print(f"{r['순위']:>3} {r['종목코드']:<7} {r['종목명']:<14} "
              f"{(r['현재가'] or 0):>10,} {(f'{rate:+.2f}%' if rate is not None else '-'):>8} "
              f"{(r['시가총액(억원)'] or 0):>14,}")

    save_csv(rows, args.out)
    print(f"\n총 {len(rows)}개 종목을 {args.out}에 저장했습니다.")
    if args.xlsx:
        save_excel(summary, rows, args.xlsx)
        print(f"엑셀도 저장했습니다: {args.xlsx}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
