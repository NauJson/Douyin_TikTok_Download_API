import os
import zipfile

import aiofiles
import httpx
import yaml
from fastapi import APIRouter, Request, Query, HTTPException  # 导入FastAPI组件
from starlette.responses import FileResponse

from app.api.models.APIResponseModel import ErrorResponseModel  # 导入响应模型
from crawlers.hybrid.hybrid_crawler import HybridCrawler  # 导入混合数据爬虫

router = APIRouter()
HybridCrawler = HybridCrawler()

# 读取上级再上级目录的配置文件
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'config.yaml')
with open(config_path, 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)

async def fetch_data(url: str, headers: dict = None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    } if headers is None else headers.get('headers')
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()  # 确保响应是成功的
        return response

# 下载视频专用
async def fetch_data_stream(url: str, request:Request , headers: dict = None, file_path: str = None):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    } if headers is None else headers.get('headers')
    async with httpx.AsyncClient() as client:
        # 启用流式请求
        async with client.stream("GET", url, headers=headers) as response:
            response.raise_for_status()

            # 流式保存文件
            async with aiofiles.open(file_path, 'wb') as out_file:
                async for chunk in response.aiter_bytes():
                    if await request.is_disconnected():
                        print("客户端断开连接，清理未完成的文件")
                        await out_file.close()
                        os.remove(file_path)
                        return False
                    await out_file.write(chunk)
            return True

def get_download_path_and_name(data, prefix, with_watermark, config):
    data_type = data.get('type')
    platform = data.get('platform')
    aweme_id = data.get('aweme_id')
    desc = data.get('desc')
    file_prefix = config.get("API").get("Download_File_Prefix") if prefix else ''
    download_path = os.path.join(config.get("API").get("Download_Path"), f"{platform}_{data_type}")
    os.makedirs(download_path, exist_ok=True)
    if data_type == 'video':
        file_name = f"{file_prefix}{platform}_{aweme_id}_{desc}.mp4" if not with_watermark else f"{file_prefix}{platform}_{aweme_id}_watermark.mp4"
        file_path = os.path.join(download_path, file_name)
        return data_type, file_path, file_name, download_path
    elif data_type == 'image':
        zip_file_name = f"{file_prefix}{platform}_{aweme_id}_images.zip" if not with_watermark else f"{file_prefix}{platform}_{aweme_id}_images_watermark.zip"
        zip_file_path = os.path.join(download_path, zip_file_name)
        return data_type, zip_file_path, zip_file_name, download_path
    else:
        return data_type, None, None, download_path

async def download_file_common(request, url, prefix, with_watermark, config):
    try:
        data = await HybridCrawler.hybrid_parsing_single_video(url, minimal=True)
    except Exception as e:
        code = 400
        return ErrorResponseModel(code=code, message=str(e), router=request.url.path, params=dict(request.query_params))

    try:
        data_type, file_path, file_name, download_path = get_download_path_and_name(data, prefix, with_watermark, config)
        if data_type == 'video':
            if os.path.exists(file_path):
                return FileResponse(path=file_path, media_type='video/mp4', filename=file_name)
            video_url = data.get('video_data').get('nwm_video_url_HQ') if not with_watermark else data.get('video_data').get('wm_video_url_HQ')
            __headers = await HybridCrawler.TikTokWebCrawler.get_tiktok_headers() if data.get('platform') == 'tiktok' else await HybridCrawler.DouyinWebCrawler.get_douyin_headers()
            success = await fetch_data_stream(video_url, request, headers=__headers, file_path=file_path)
            if not success:
                raise HTTPException(status_code=500, detail="An error occurred while fetching data")
            return FileResponse(path=file_path, filename=file_name, media_type="video/mp4")
        elif data_type == 'image':
            if os.path.exists(file_path):
                return FileResponse(path=file_path, filename=file_name, media_type="application/zip")
            urls = data.get('image_data').get('no_watermark_image_list') if not with_watermark else data.get('image_data').get('watermark_image_list')
            image_file_list = []
            file_prefix = config.get("API").get("Download_File_Prefix") if prefix else ''
            platform = data.get('platform')
            aweme_id = data.get('aweme_id')
            for url_img in urls:
                response = await fetch_data(url_img)
                index = int(urls.index(url_img))
                content_type = response.headers.get('content-type')
                file_format = content_type.split('/')[1]
                img_file_name = f"{file_prefix}{platform}_{aweme_id}_{index + 1}.{file_format}" if not with_watermark else f"{file_prefix}{platform}_{aweme_id}_{index + 1}_watermark.{file_format}"
                img_file_path = os.path.join(download_path, img_file_name)
                image_file_list.append(img_file_path)
                async with aiofiles.open(img_file_path, 'wb') as out_file:
                    await out_file.write(response.content)
            with zipfile.ZipFile(file_path, 'w') as zip_file:
                for image_file in image_file_list:
                    zip_file.write(image_file, os.path.basename(image_file))
            return FileResponse(path=file_path, filename=file_name, media_type="application/zip")
        else:
            return ErrorResponseModel(code=400, message="不支持的数据类型", router=request.url.path, params=dict(request.query_params))
    except Exception as e:
        print(e)
        code = 400
        return ErrorResponseModel(code=code, message=str(e), router=request.url.path, params=dict(request.query_params))

@router.get("/download", summary="在线下载抖音|TikTok视频/图片/Online download Douyin|TikTok video/image")
async def download_file_hybrid(request: Request,
                               url: str = Query(
                                   example="https://www.douyin.com/video/7372484719365098803",
                                   description="视频或图片的URL地址，也支持抖音|TikTok的分享链接，例如：https://v.douyin.com/e4J8Q7A/"),
                               prefix: bool = True,
                               with_watermark: bool = False):
    """
    # [中文]
    ### 用途:
    - 在线下载抖音|TikTok 无水印或有水印的视频/图片
    - 通过传入的视频URL参数，获取对应的视频或图片数据，然后下载到本地。
    - 如果你在尝试直接访问TikTok单一视频接口的JSON数据中的视频播放地址时遇到HTTP403错误，那么你可以使用此接口来下载视频。
    - 这个接口会占用一定的服务器资源，所以在Demo站点是默认关闭的，你可以在本地部署后调用此接口。
    ### 参数:
    - url: 视频或图片的URL地址，也支持抖音|TikTok的分享链接，例如：https://v.douyin.com/e4J8Q7A/。
    - prefix: 下载文件的前缀，默认为True，可以在配置文件中修改。
    - with_watermark: 是否下载带水印的视频或图片，默认为False。
    ### 返回:
    - 返回下载的视频或图片文件响应。

    # [English]
    ### Purpose:
    - Download Douyin|TikTok video/image with or without watermark online.
    - By passing the video URL parameter, get the corresponding video or image data, and then download it to the local.
    - If you encounter an HTTP403 error when trying to access the video playback address in the JSON data of the TikTok single video interface directly, you can use this interface to download the video.
    - This interface will occupy a certain amount of server resources, so it is disabled by default on the Demo site, you can call this interface after deploying it locally.
    ### Parameters:
    - url: The URL address of the video or image, also supports Douyin|TikTok sharing links, for example: https://v.douyin.com/e4J8Q7A/.
    - prefix: The prefix of the downloaded file, the default is True, and can be modified in the configuration file.
    - with_watermark: Whether to download videos or images with watermarks, the default is False.
    ### Returns:
    - Return the response of the downloaded video or image file.

    # [示例/Example]
    url: https://www.douyin.com/video/7372484719365098803
    """
    # 是否开启此端点/Whether to enable this endpoint
    if not config["API"]["Download_Switch"]:
        code = 400
        message = "Download endpoint is disabled in the configuration file. | 配置文件中已禁用下载端点。"
        return ErrorResponseModel(code=code, message=message, router=request.url.path,
                                  params=dict(request.query_params))

    return await download_file_common(request, url, prefix, with_watermark, config)
