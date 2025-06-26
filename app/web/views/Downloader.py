from pywebio.output import popup, put_markdown, put_html, put_text, put_link
from app.web.views.ViewsUtils import ViewsUtils
from pywebio.input import input as pywebio_input
import httpx

t = ViewsUtils().t


# 下载器弹窗/Downloader pop-up
def downloader_pop_window():
    with popup(t("💾 下载器", "💾 Downloader")):
        put_markdown(t("> 桌面端下载器", "> Desktop Downloader"))
        put_markdown(t("你可以使用下面的开源项目在桌面端下载视频：",
                       "You can use the following open source projects to download videos on the desktop:"))
        put_markdown("1. [TikTokDownload](https://github.com/Johnserf-Seed/TikTokDownload)")
        put_markdown(t("> 备注", "> Note"))
        put_markdown(t("1. 请注意下载器的使用规范，不要用于违法用途。",
                       "1. Please pay attention to the use specifications of the downloader and do not use it for illegal purposes."))
        put_markdown(t("2. 下载器相关问题请咨询对应项目的开发者。",
                       "2. For issues related to the downloader, please consult the developer of the corresponding project."))

# 一键下载用户主页全部视频弹窗
async def download_user_all_videos_pop_window():
    from pywebio.output import popup, put_loading, close_popup, put_table, put_success, put_error
    from pywebio.session import run_async
    with popup(t("⬇️一键下载用户主页全部视频", "⬇️Batch Download All User Videos")):
        url = pywebio_input(t("请输入抖音主页链接：", "Please input Douyin homepage url:"), required=True)
        put_loading(t("正在请求后端批量下载，请稍候...", "Requesting backend to batch download, please wait..."))
        try:
            async with httpx.AsyncClient(timeout=600) as client:
                resp = await client.post("/api/douyin_web/download_user_all_videos", json={"url": url})
                data = resp.json()
                close_popup()
                if data.get("code") == 200:
                    put_success(t("全部下载任务已提交，结果如下：", "All download tasks submitted, result as below:"))
                    table_data = [[t("视频ID", "Aweme ID"), t("状态", "Status"), t("文件路径", "File Path")]]
                    for item in data.get("data", []):
                        table_data.append([
                            item.get("aweme_id"),
                            t("成功", "Success") if item.get("success") else t("失败", "Failed"),
                            item.get("file_path", "-")
                        ])
                    put_table(table_data)
                else:
                    put_error(t("下载失败：", "Download failed:") + str(data.get("message", data)))
        except Exception as e:
            close_popup()
            put_error(t("请求异常：", "Request error:") + str(e))
