#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 1. 手动填入你的 Gemini API Key
API_KEY = "AIzaSyA3SZEH-AlgA22lfyNduKJra6rpV7P37FU"

from google import genai
from google.genai import errors  # 用于捕获 ServerError
from PIL import Image


def test_text_only(client: genai.Client):
    """用普通文本模型做一个最简单的 ping，验证 key 和网络是否正常。"""
    print("=== 文本模型连通性检查 ===")
    resp = client.models.generate_content(
        model="gemini-2.5-flash",   # 纯文本模型
        contents=["ping"],
    )
    print("文本模型返回：", resp.text.strip())
    print("=== 文本 OK ===\n")


def test_image_edit(client: genai.Client):
    """
    使用 gemini-2.5-flash-image 做图片编辑：
    读取当前目录 test.png，编辑后输出到 result.png
    """
    print("=== 图片编辑测试 ===")

    prompt = (
        "Slightly enhance the colors and contrast, "
        "and add a soft cinematic lighting effect to this image."
    )

    input_path = "test.png"
    output_path = "result.png"

    # 读取当前目录下的 test.png
    image = Image.open(input_path)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-image",
            contents=[prompt, image],
        )
    except errors.ServerError as e:
        # 把服务端 500 的信息打印出来，方便你后面排查 / 发给官方
        print("调用 gemini-2.5-flash-image 出现 ServerError (500)：")
        print(e)
        return

    # 尝试从返回内容中取出图片
    saved = False
    for part in response.parts:
        if part.inline_data is not None:
            out_img = part.as_image()
            out_img.save(output_path)
            print(f"图片已保存到: {output_path}")
            saved = True
            break

    if not saved:
        print("没有在响应中找到图片数据，完整响应如下：")
        print(response)

    print("=== 图片编辑测试结束 ===")


def main():
    # 用你手动填的 API_KEY 初始化客户端
    client = genai.Client(api_key=API_KEY)

    # 先测文本，确认 key / 账号 / 网络一切正常
    test_text_only(client)

    # 再测图片编辑
    test_image_edit(client)


if __name__ == "__main__":
    main()
