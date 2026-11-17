# 短视频复盘室

[打开工作台](https://zhanyina1205-ai.github.io/short-video-review-studio/)

导入抖音、小红书后台截图，核对指标后生成单条复盘。同一作品可按观察时间补录。

## 在线使用

首次识别截图时，页面会下载中文和英文 OCR 模型。图片识别与数据分析均在浏览器内运行。清除站点数据会移除本浏览器的档案。浏览器档案与 Mac 本地档案独立。

在北京时间周一 10 点之后打开工作台，即可看到已归档作品的上一发布周汇总。网页关闭期间的周一定时交付由已配置的本机 Codex 自动任务负责。

## 本机版本

在装有 Python 3 与 Xcode Command Line Tools 的 Mac 上双击「启动短视频复盘室.command」。本机版使用 Apple Vision 识别截图，作品档案保存在 ~/Documents/短视频复盘。随附的 skill 目录可安装为 Codex 的 video-review-studio 技能。

## 构建网页版

运行 npm ci 和 npm run build，再用静态服务器提供 dist 目录。推送 main 后由 GitHub Actions 构建并发布。
