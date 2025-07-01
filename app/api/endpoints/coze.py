from runtime import Args
from typings.extract_txt_from_douyin_share.extract_txt_from_douyin_share import Input, Output
import requests

"""
Each file needs to export a function named `handler`. This function is the entrance to the Tool.

Parameters:
args: parameters of the entry function.
args.input - input parameters, you can get test input value by args.input.xxx.
args.logger - logger instance used to print logs, injected by runtime.

Remember to fill in input/output in Metadata, it helps LLM to recognize and use tool.

Return:
The return data of the function, which should match the declared output parameters.
"""
def handler(args: Args[Input])->Output:
    url = "https://douyin.lzdll6.fun:3443/api/douyin/web/hello"
    headers = {"accept": "application/json"}
    response = requests.get(url, headers=headers)
    response_json = response.json()
    message = response_json.get("message", "")
    return {"video_txt": message}