import sys
import os
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSpinBox
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
from qfluentwidgets import (LineEdit, ComboBox, PushButton, TextEdit, BodyLabel,
                            MessageBox, CheckBox, IndeterminateProgressBar)
import yt_dlp
import images

class YTDLPInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("小白视频下载器")
        self.resize(800, 600)

        self.setWindowIcon(QIcon(':/pic/favicon.png'))

        container = QWidget()
        self.setCentralWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(20)

        self.progress_bar = IndeterminateProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.url_entry = LineEdit()
        self.url_entry.setPlaceholderText("请输入视频或播放列表URL（支持多个URL，用空格分隔）")
        self.url_entry.setClearButtonEnabled(True)
        self.url_entry.setText('https://www.bilibili.com/video/BV1iW9RYWEiJ/')
        layout.addWidget(BodyLabel("视频/播放列表URL:"))
        layout.addWidget(self.url_entry)

        self.format_combo = ComboBox()
        self.format_combo.addItems([
            "最高质量（自动合并音视频）",
            "仅最佳视频",
            "仅最佳音频"
        ])
        layout.addWidget(BodyLabel("下载格式:"))
        layout.addWidget(self.format_combo)

        self.path_entry = LineEdit()
        self.path_entry.setPlaceholderText("默认路径：./downloads")
        self.path_entry.setClearButtonEnabled(True)
        layout.addWidget(BodyLabel("保存路径:"))
        layout.addWidget(self.path_entry)

        self.subtitle_checkbox = CheckBox("下载字幕（自动选择英简中文字幕）")
        self.subtitle_checkbox.setChecked(True)
        layout.addWidget(self.subtitle_checkbox)

        self.metadata_checkbox = CheckBox("添加元数据信息（需要ffmpeg）")
        self.metadata_checkbox.setChecked(True)
        layout.addWidget(self.metadata_checkbox)

        playlist_layout = QHBoxLayout()
        self.playlist_checkbox = CheckBox("下载整个播放列表")
        self.playlist_checkbox.setChecked(False)
        playlist_layout.addWidget(self.playlist_checkbox)

        self.playlist_limit_label = BodyLabel("下载数量限制:")
        self.playlist_limit = QSpinBox()
        self.playlist_limit.setRange(1, 1000)
        self.playlist_limit.setValue(100)
        self.playlist_limit.setEnabled(False)
        playlist_layout.addWidget(self.playlist_limit_label)
        playlist_layout.addWidget(self.playlist_limit)
        playlist_layout.addStretch()
        layout.addLayout(playlist_layout)

        self.playlist_checkbox.stateChanged.connect(self.toggle_playlist_limit)

        button_layout = QHBoxLayout()
        self.list_formats_button = PushButton("列出可用格式")
        self.list_formats_button.clicked.connect(self.list_formats)
        button_layout.addWidget(self.list_formats_button)

        self.download_button = PushButton("开始下载")
        self.download_button.clicked.connect(self.start_download)
        button_layout.addWidget(self.download_button)
        layout.addLayout(button_layout)

        layout.addWidget(BodyLabel("下载日志:"))
        self.output_text = TextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)

    def toggle_playlist_limit(self, state):
        self.playlist_limit.setEnabled(state == Qt.Checked)

    def build_options(self, url, list_formats=False):
        output_path = self.path_entry.text() or "./downloads"
        os.makedirs(output_path, exist_ok=True)

        ydl_opts = {
            'outtmpl': f'{output_path}/%(playlist_title)s/%(title)s [%(id)s].%(ext)s',
            'progress_hooks': [self.progress_hook],
            'quiet': False,
            'noprogress': False,
        }

        if list_formats:
            ydl_opts['listformats'] = True
        else:
            format_choice = self.format_combo.currentText()
            if format_choice == "最高质量（自动合并音视频）":
                if 'bilibili' in url:
                    ydl_opts['format'] = 'bestvideo+bestaudio/best'
                else:
                    ydl_opts['format'] = 'bv[ext=webm]+ba[ext=m4a]'
                ydl_opts['merge_output_format'] = 'mp4'
                ydl_opts['embed_thumbnail'] = True
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                }]
            elif format_choice == "仅最佳视频":
                ydl_opts['format'] = 'bestvideo'
            else:  # 仅最佳音频
                ydl_opts['format'] = 'bestaudio'

            if self.subtitle_checkbox.isChecked():
                ydl_opts['writesubtitles'] = True
                ydl_opts['writeautomaticsub'] = True
                ydl_opts['subtitleslangs'] = ['en', 'zh-Hans']

            if self.metadata_checkbox.isChecked():
                ydl_opts['embed_thumbnail'] = True
                ydl_opts['postprocessors'] = ydl_opts.get('postprocessors', []) + [{
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                }]

            if self.playlist_checkbox.isChecked():
                ydl_opts['noplaylist'] = False
                ydl_opts['playlist_items'] = f'1-{self.playlist_limit.value()}'
            else:
                ydl_opts['noplaylist'] = True

        return ydl_opts

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            self.output_text.append(f"[download] {d.get('_percent_str', '0%')} of {d.get('filename', 'unknown')}")
        elif d['status'] == 'finished':
            self.output_text.append(f"[download] Completed: {d.get('filename', 'unknown')}")
        QApplication.processEvents()

    def start_download(self):
        urls = self.url_entry.text().split()
        if not urls:
            MessageBox("错误", "请输入至少一个视频或播放列表URL", self).exec()
            return

        self.download_button.setEnabled(False)
        self.list_formats_button.setEnabled(False)
        self.progress_bar.show()

        thread = threading.Thread(target=self.run_downloads, args=(urls,))
        thread.start()

    def list_formats(self):
        urls = self.url_entry.text().split()
        if not urls:
            MessageBox("错误", "请输入至少一个视频或播放列表URL", self).exec()
            return

        self.output_text.clear()
        self.download_button.setEnabled(False)
        self.list_formats_button.setEnabled(False)
        self.progress_bar.show()

        thread = threading.Thread(target=self.run_list_formats, args=(urls,))
        thread.start()

    def run_list_formats(self, urls):
        try:
            with yt_dlp.YoutubeDL() as ydl:
                for url in urls:
                    self.output_text.append(f"正在获取格式列表：{url}")
                    opts = self.build_options(url, list_formats=True)
                    info = ydl.extract_info(url, download=False)
                    for format in info.get('formats', []):
                        self.output_text.append(f"{format['format_id']} - {format['ext']} - {format.get('format_note', '')}")
                    self.output_text.append(f"✓ 格式列表获取完成：{url}\n")
        except Exception as e:
            self.output_text.append(f"错误: {str(e)}")
        finally:
            self.download_button.setEnabled(True)
            self.list_formats_button.setEnabled(True)
            self.progress_bar.hide()

    def run_downloads(self, urls):
        try:
            for url in urls:
                opts = self.build_options(url)
                self.output_text.append(f"开始下载：{url}")
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([url])
                self.output_text.append(f"✓ 下载完成：{url}\n")
        except Exception as e:
            self.output_text.append(f"错误: {str(e)}")
            self.output_text.append("提示：请检查URL是否有效或调整下载设置。\n")
        finally:
            self.download_button.setEnabled(True)
            self.list_formats_button.setEnabled(True)
            self.progress_bar.hide()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = YTDLPInterface()
    window.show()
    sys.exit(app.exec())