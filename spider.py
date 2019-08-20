import json
import re

import requests
from lxml import etree
import pymysql
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
import time

headers = {
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.87 Safari/537.36'
}


# 获取视频id,名字，图片
def get_video_id(url, page):
    time.sleep(1)
    url = url + str(page)
    s = requests.session()
    s.keep_alive = False
    res = s.get(url, headers=headers)
    html = etree.HTML(res.content)
    for rows in range(1, 41):
        rows = str(rows)
        video_id = html.xpath("//li[" + rows + "]/@id")
        episode_url = html.xpath("//li[" + rows + "]/div/a/@href")
        video_img = html.xpath("//li[" + rows + "]/div/a/span[1]/img/@src")
        video_name = html.xpath("//li[" + rows + "]/div/a/span[2]/text()")
        if len(video_id):
            arry = get_more_info(str(episode_url[0]), video_id)
            movie_insert(video_id[0], video_name[0], video_img[0], episode_url[0], arry[2], arry[1], arry[0], arry[4],
                         arry[3])
        else:
            break

    return 0


def get_episode_url(episode_url):
    country = ""
    url = "https://www.crunchyroll.com" + country + episode_url[0]
    res = requests.get(url, headers=headers)
    try:
        data = res.text
        data = re.findall("vilos\.config\.media = ([\w\W]*?)\}\]\};", data)
        if len(data) == 0:
            print("未找到资源----")
            return
        data = data[0] + "}]}"
        data = json.loads(data)
        url_m3u8 = []
        for u in data['streams']:
            if u["url"].find(".m3u8") != -1:
                url_m3u8.append(u)
    except Exception as e:
        print(e)
    return url_m3u8
    # return json.dumps({"list": url_m3u8})
    # 获取视频评分，描述，年份，分类


def get_more_info(name, movie_id):
    movie_url = "https://www.crunchyroll.com" + name + "/videos"
    s = requests.session()
    s.keep_alive = False
    res = s.get(movie_url, headers=headers)
    html = etree.HTML(res.content)
    video_info = html.xpath("//*[@id='sidebar_elements']/li[3]/p[2]/span[2]/text()")
    if len(video_info) == 0:
        video_info = html.xpath("//*[@id='sidebar_elements']/li[2]/p[2]/span[2]/text()")
    if len(video_info) == 0:
        video_info = html.xpath("//*[@id='sidebar_elements']/li[2]/p/span[1]/text()")
    video_mark = html.xpath("//*[@id='sidebar_elements']/li[3]/div/div[2]/span/span/@content")
    video_publisher = html.xpath("//*[@id='sidebar_elements']/li[5]/ul/li[1]/a/text()")
    video_tag = html.xpath('//*[@id="sidebar_elements"]/li[5]/ul/li[3]/a')
    video_year = html.xpath("//*[@id='sidebar_elements']/li[5]/ul/li[2]/text()")
    # 获取剧集信息
    count = 1
    while True:
        rows = str(count)
        episode_number = html.xpath("//*[@id='showview_content_videos']/ul/li/ul/li[" + rows + "]/div/a/span/text()")
        episode_img = html.xpath("//*[@id='showview_content_videos']/ul/li/ul/li[" + rows + "]/div/a/img/@src")
        episode_url = html.xpath("//*[@id='showview_content_videos']/ul/li/ul/li[" + rows + "]/div/a/@href")
        episode_name = html.xpath("//*[@id='showview_content_videos']/ul/li/ul/li[" + rows + "]/div/a/img/@alt")
        if len(episode_number) == 0:
            break
        if len(episode_img) == 0:
            episode_img.append('null')
        # 保存图片
        # episode_img[0] = save_image(name, episode_img[0])
        episode_name = str(episode_name[0]).replace(' ', '').replace(',', ' ').replace("\"", "\'")
        episode_info = get_episode_info(episode_url)
        episodes = get_episode_url(episode_url)
        # 剧集信息入库
        episode_insert(movie_id[0], episode_number[0].replace(' ', '').replace('/n', ''), episode_name, episode_img[0],
                       episodes, episode_info)
        count = count + 1
    if len(video_publisher) == 0:
        video_publisher.append('')
    if len(video_mark) == 0:
        video_mark.append(0)
    if len(video_info) == 0:
        video_info.append("null")
    if len(video_year) == 0:
        video_year.append('')
    if len(video_tag) == 0:
        video_tag.append("")
    # 返回动漫信息
    return video_info[0], video_mark[0], video_publisher[0], video_year[0], video_tag[0]


# 获取剧集介绍
def get_episode_info(episode_url):
    s = requests.session()
    s.keep_alive = False
    res = s.get("https://www.crunchyroll.com/" + episode_url[0], headers=headers)
    html = etree.HTML(res.content)
    episode_info_1 = html.xpath("//*[@id='showmedia_about_info']/p/text()")
    if len(episode_info_1) == 0:
        return " "
    episode_info_2 = html.xpath("//*[@id='showmedia_about_info']/p/span[1]/text()")
    episode_info = episode_info_1[0] + episode_info_2[0]
    return episode_info


# 将剧集信息保存进入Mysql
def episode_insert(movie_id, episode_number, episode_name, episode_img, episode_url, episode_info):
    db = pymysql.connect("localhost", "root", "root@cpx", "shows")
    cursor = db.cursor()
    sql = 'insert into episode(movie_id,episode_number,episode_name,episode_img,episode_url,download,episode_info) ' \
          'values("%s","%s","%s","%s","%s",%s,"%s")' % \
          (movie_id, episode_number, db.escape(episode_name), episode_img, episode_url, 0, db.escape(episode_info))
    try:
        cursor.execute(sql)
        db.commit()
        print(episode_name + "保存成功")

    except Exception as e:
        print(e + 'err:' + sql)
        db.rollback()
        raise
    db.close()


# 将动漫信息存入数据库
def movie_insert(movie_id, movie_name, img_url, movie_url, publisher, movie_mark, info, movie_type, movie_year):
    db = pymysql.connect("localhost", "root", "root@cpx", "shows")
    cursor = db.cursor()
    info = info.replace("\"", "\'")
    movie_name.replace("\"", "\'")
    # img_url = save_image(movie_name, img_url)
    sql = 'insert into movie values("%s","%s","%s","%s","%s","%s","%s","%s","%s")' % \
          (movie_id, movie_name, img_url, movie_url, publisher, movie_type, movie_mark, movie_year, info)
    try:
        cursor.execute(sql)
        db.commit()
        print("video_name " + str(movie_name) + " insert suecess")
    except:
        print("err:" + sql)
        db.rollback()
        raise
    db.close()


# 保存剧集图片到本地
# def save_image(movie_name, image_url):
#     try:
#         if image_url.find("http") == -1:
#             return ""
#         image_path = "/crunchyroll_image" + movie_name
#         data = requests.get(image_url)
#         if not os.path.exists(image_path):
#             os.mkdir(image_path)
#         episode_path = str(uuid.uuid1()) + ".jpg"
#         with open(image_path + "/" + episode_path, "wb") as f:
#             f.write(data.content)
#     except Exception as e:
#         print(e)
#         raise
#     print("----下载成功------")
#     episode_path = movie_name + "/" + episode_path
#     return episode_path


if __name__ == "__main__":
    pool = ThreadPoolExecutor(1)
    print("begin")
    url = "https://www.crunchyroll.com/videos/anime/popular/ajax_page?pg="
    for page in range(0, 41):
        # pool.submit(get_video_id, url, page)
        get_video_id(url, page)
    print("end")
