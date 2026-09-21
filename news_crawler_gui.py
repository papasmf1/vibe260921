"""네이버 뉴스 크롤러 GUI (PyQt6).

news_crawler.py 의 크롤링 함수를 그대로 사용하고, 화면과 백그라운드 스레드만 추가한 앱이다.

실행:  python news_crawler_gui.py
필요 패키지: pip install PyQt6 requests beautifulsoup4
"""
import json
import sys
from urllib.parse import quote

import requests
from PyQt6.QtCore import QThread, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton, QSpinBox, QSplitter,
    QTableWidget, QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget,
)

import news_crawler as nc

SEARCH_URL = "https://search.naver.com/search.naver?where=nexearch&ie=utf8&query={}"


class CrawlWorker(QThread):
    """검색 -> 기사별 본문 수집을 UI 멈춤 없이 수행한다."""

    status = pyqtSignal(str)
    progress = pyqtSignal(int, int)      # 현재, 전체
    article = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, url, count, parent=None):
        super().__init__(parent)
        self.url = url
        self.count = count
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            self.status.emit("검색 페이지를 요청하는 중...")
            links = nc.search_articles(self.url)
        except requests.RequestException as e:
            self.failed.emit(f"검색 페이지 요청 실패: {e}")
            return
        if not links:
            self.failed.emit("기사 링크를 찾지 못했습니다. 네이버 페이지 구조가 바뀌었을 수 있습니다.")
            return

        seen_titles, done = set(), 0
        self.progress.emit(0, self.count)
        for i, item in enumerate(links, 1):
            if self._stop or done >= self.count:
                break
            self.status.emit(f"[{i}/{len(links)}] {item['title'] or item['url']}")
            try:
                art = nc.crawl_article(item["url"])
                # 원문 사이트가 본문을 막은 경우 네이버뉴스 사본으로 대체
                if len(art["content"]) < 150 and item.get("naver_url"):
                    alt = nc.crawl_article(item["naver_url"])
                    if len(alt["content"]) > len(art["content"]):
                        art["content"] = alt["content"]
                        art["content_source"] = item["naver_url"]
            except requests.RequestException as e:
                self.status.emit(f"실패: {e}")
                continue
            if art["title"] in seen_titles:
                continue
            seen_titles.add(art["title"])
            done += 1
            self.article.emit(art)
            self.progress.emit(done, self.count)
            self.msleep(800)  # 서버 부담을 줄이기 위한 요청 간격


class MainWindow(QMainWindow):
    COLS = ["제목", "언론사", "발행일"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("네이버 뉴스 크롤러")
        self.resize(1100, 700)
        self.articles = []
        self.worker = None

        # --- 상단 입력줄 ---
        self.query_edit = QLineEdit("반도체")
        self.query_edit.setPlaceholderText("검색어 또는 네이버 검색 결과 URL")
        self.query_edit.returnPressed.connect(self.start)
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 30)
        self.count_spin.setValue(5)
        self.start_btn = QPushButton("수집 시작")
        self.start_btn.clicked.connect(self.start)
        self.stop_btn = QPushButton("중지")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop)

        top = QHBoxLayout()
        top.addWidget(QLabel("검색어/URL"))
        top.addWidget(self.query_edit, 1)
        top.addWidget(QLabel("기사 수"))
        top.addWidget(self.count_spin)
        top.addWidget(self.start_btn)
        top.addWidget(self.stop_btn)

        # --- 기사 목록 + 본문 보기 ---
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.show_selected)

        self.viewer = QTextBrowser()
        self.viewer.setOpenLinks(False)
        self.viewer.anchorClicked.connect(QDesktopServices.openUrl)
        self.viewer.setPlaceholderText("왼쪽 목록에서 기사를 선택하면 본문이 표시됩니다.")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.table)
        splitter.addWidget(self.viewer)
        splitter.setSizes([450, 650])

        # --- 하단 상태줄 ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.save_btn = QPushButton("JSON 저장")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_json)
        self.excel_btn = QPushButton("엑셀 저장")
        self.excel_btn.setEnabled(False)
        self.excel_btn.clicked.connect(self.save_excel)
        self.clear_btn = QPushButton("목록 지우기")
        self.clear_btn.clicked.connect(self.clear_all)
        bottom = QHBoxLayout()
        bottom.addWidget(self.progress_bar, 1)
        bottom.addWidget(self.clear_btn)
        bottom.addWidget(self.save_btn)
        bottom.addWidget(self.excel_btn)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addLayout(top)
        layout.addWidget(splitter, 1)
        layout.addLayout(bottom)
        self.setCentralWidget(central)
        self.statusBar().showMessage("검색어를 입력하고 [수집 시작]을 누르세요.")

    # ---------- 동작 ----------
    def build_url(self):
        text = self.query_edit.text().strip()
        if not text:
            return ""
        if text.lower().startswith(("http://", "https://")):
            return text
        return SEARCH_URL.format(quote(text))

    def start(self):
        if self.worker and self.worker.isRunning():
            return
        url = self.build_url()
        if not url:
            QMessageBox.information(self, "알림", "검색어 또는 URL을 입력하세요.")
            return
        self.clear_all()
        self.set_running(True)
        self.worker = CrawlWorker(url, self.count_spin.value(), self)
        self.worker.status.connect(self.statusBar().showMessage)
        self.worker.progress.connect(self.on_progress)
        self.worker.article.connect(self.add_article)
        self.worker.failed.connect(self.on_failed)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.statusBar().showMessage("중지하는 중... (진행 중인 요청이 끝나면 멈춥니다)")
            self.stop_btn.setEnabled(False)

    def set_running(self, running):
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.query_edit.setEnabled(not running)
        self.count_spin.setEnabled(not running)

    def on_progress(self, cur, total):
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(cur)
        self.progress_bar.setFormat(f"{cur} / {total}")

    def add_article(self, art):
        self.articles.append(art)
        row = self.table.rowCount()
        self.table.insertRow(row)
        published = art["published"][:16].replace("T", " ") if art["published"] else "-"
        for col, text in enumerate([art["title"], art["press"] or "-", published]):
            self.table.setItem(row, col, QTableWidgetItem(text))
        self.save_btn.setEnabled(True)
        self.excel_btn.setEnabled(True)
        if row == 0:
            self.table.selectRow(0)

    def on_failed(self, msg):
        self.statusBar().showMessage(msg)
        QMessageBox.warning(self, "수집 실패", msg)

    def on_finished(self):
        self.set_running(False)
        if self.articles:
            self.statusBar().showMessage(f"완료: {len(self.articles)}건 수집")

    def show_selected(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        art = self.articles[rows[0].row()]
        esc = lambda s: (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        body = esc(art["content"]).replace("\n", "<br>")
        source = art.get("content_source")
        note = f"<p style='color:#888'>※ 본문은 네이버뉴스 사본에서 가져왔습니다.</p>" if source else ""
        self.viewer.setHtml(
            f"<h2>{esc(art['title'])}</h2>"
            f"<p style='color:#666'>{esc(art['press'] or '-')} · {esc(art['published'] or '-')}<br>"
            f"<a href='{art['url']}'>{esc(art['url'])}</a></p>{note}<hr><p>{body}</p>"
        )

    def save_json(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "JSON으로 저장", "news_result.json", "JSON (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.articles, f, ensure_ascii=False, indent=2)
        self.statusBar().showMessage(f"{len(self.articles)}건을 저장했습니다: {path}")

    def save_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "엑셀로 저장", "news_result.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            nc.save_excel(self.articles, path)
        except ImportError:
            QMessageBox.warning(self, "패키지 필요", "openpyxl이 필요합니다.\npip install openpyxl")
            return
        except PermissionError:
            QMessageBox.warning(self, "저장 실패", "파일이 엑셀에서 열려 있습니다. 닫고 다시 시도하세요.")
            return
        except OSError as e:
            QMessageBox.warning(self, "저장 실패", str(e))
            return
        self.statusBar().showMessage(f"{len(self.articles)}건을 엑셀로 저장했습니다: {path}")

    def clear_all(self):
        if self.worker and self.worker.isRunning():
            return
        self.articles.clear()
        self.table.setRowCount(0)
        self.viewer.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("")
        self.save_btn.setEnabled(False)
        self.excel_btn.setEnabled(False)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(5000)
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
