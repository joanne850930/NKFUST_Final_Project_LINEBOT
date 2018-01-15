import requests
import re
import random
import configparser
from bs4 import BeautifulSoup
from flask import Flask, request, abort,render_template
from imgurpython import ImgurClient

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import *

app = Flask(__name__)
config = configparser.ConfigParser()
config.read("/home/jc0424057/line-bot-tutorial-master/config.ini")

line_bot_api = LineBotApi(config['line_bot']['Channel_Access_Token'])
handler = WebhookHandler(config['line_bot']['Channel_Secret'])
#client_id = config['imgur_api']['Client_ID']
#client_secret = config['imgur_api']['Client_Secret']
#album_id = config['imgur_api']['Album_ID']
#API_Get_Image = config['other_api']['API_Get_Image']


@app.route("/")
def index():
   return render_template("template/index.html")


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    # print("body:",body)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'ok'


def pattern_mega(text):
    patterns = [
        'mega', 'mg', 'mu', 'ＭＥＧＡ', 'ＭＥ', 'ＭＵ',
        'ｍｅ', 'ｍｕ', 'ｍｅｇａ', 'GD', 'MG', 'google',
    ]
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True


def eyny_movie():
    target_url = 'http://www.eyny.com/forum-205-1.html'
    print('Start parsing eynyMovie....')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ''
    for titleURL in soup.select('.bm_c tbody .xst'):
        if pattern_mega(titleURL.text):
            title = titleURL.text
            if '11379780-1-3' in titleURL['href']:
                continue
            link = 'http://www.eyny.com/' + titleURL['href']
            data = '{}\n{}\n\n'.format(title, link)
            content += data
    return content


def apple_news():
    target_url = 'http://www.appledaily.com.tw/realtimenews/section/new/'
    head = 'http://www.appledaily.com.tw'
    print('Start parsing appleNews....')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""
    for index, data in enumerate(soup.select('.rtddt a'), 0):
        if index == 15:
            return content
        if head in data['href']:
            link = data['href']
        else:
            link = head + data['href']
        content += '{}\n\n'.format(link)
    return content


def get_page_number(content):
    start_index = content.find('index')
    end_index = content.find('.html')
    page_number = content[start_index + 5: end_index]
    return int(page_number) + 1


def craw_page(res, push_rate):
    soup_ = BeautifulSoup(res.text, 'html.parser')
    article_seq = []
    for r_ent in soup_.find_all(class_="r-ent"):
        try:
            # 先得到每篇文章的篇url
            link = r_ent.find('a')['href']
            if link:
                # 確定得到url再去抓 標題 以及 推文數
                title = r_ent.find(class_="title").text.strip()
                rate = r_ent.find(class_="nrec").text
                url = 'https://www.ptt.cc' + link
                if rate:
                    rate = 100 if rate.startswith('爆') else rate
                    rate = -1 * int(rate[1]) if rate.startswith('X') else rate
                else:
                    rate = 0
                # 比對推文數
                if int(rate) >= push_rate:
                    article_seq.append({
                        'title': title,
                        'url': url,
                        'rate': rate,
                    })
        except Exception as e:
            # print('crawPage function error:',r_ent.find(class_="title").text.strip())
            print('本文已被刪除', e)
    return article_seq


def crawl_page_gossiping(res):
    soup = BeautifulSoup(res.text, 'html.parser')
    article_gossiping_seq = []
    for r_ent in soup.find_all(class_="r-ent"):
        try:
            # 先得到每篇文章的篇url
            link = r_ent.find('a')['href']

            if link:
                # 確定得到url再去抓 標題 以及 推文數
                title = r_ent.find(class_="title").text.strip()
                url_link = 'https://www.ptt.cc' + link
                article_gossiping_seq.append({
                    'url_link': url_link,
                    'title': title
                })

        except Exception as e:
            # print u'crawPage function error:',r_ent.find(class_="title").text.strip()
            # print('本文已被刪除')
            print('delete', e)
    return article_gossiping_seq


def ptt_gossiping():
    rs = requests.session()
    load = {
        'from': '/bbs/Gossiping/index.html',
        'yes': 'yes'
    }
    res = rs.post('https://www.ptt.cc/ask/over18', verify=False, data=load)
    soup = BeautifulSoup(res.text, 'html.parser')
    all_page_url = soup.select('.btn.wide')[1]['href']
    start_page = get_page_number(all_page_url)
    index_list = []
    article_gossiping = []
    for page in range(start_page, start_page - 2, -1):
        page_url = 'https://www.ptt.cc/bbs/Gossiping/index{}.html'.format(page)
        index_list.append(page_url)

    # 抓取 文章標題 網址 推文數
    while index_list:
        index = index_list.pop(0)
        res = rs.get(index, verify=False)
        # 如網頁忙線中,則先將網頁加入 index_list 並休息1秒後再連接
        if res.status_code != 200:
            index_list.append(index)
            # print u'error_URL:',index
            # time.sleep(1)
        else:
            article_gossiping = crawl_page_gossiping(res)
            # print u'OK_URL:', index
            # time.sleep(0.05)
    content = ''
    for index, article in enumerate(article_gossiping, 0):
        if index == 15:
            return content
        data = '{}\n{}\n\n'.format(article.get('title', None), article.get('url_link', None))
        content += data
    return content


def ptt_beauty():
    rs = requests.session()
    res = rs.get('https://www.ptt.cc/bbs/Beauty/index.html', verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    all_page_url = soup.select('.btn.wide')[1]['href']
    start_page = get_page_number(all_page_url)
    page_term = 2  # crawler count
    push_rate = 10  # 推文
    index_list = []
    article_list = []
    for page in range(start_page, start_page - page_term, -1):
        page_url = 'https://www.ptt.cc/bbs/Beauty/index{}.html'.format(page)
        index_list.append(page_url)

    # 抓取 文章標題 網址 推文數
    while index_list:
        index = index_list.pop(0)
        res = rs.get(index, verify=False)
        # 如網頁忙線中,則先將網頁加入 index_list 並休息1秒後再連接
        if res.status_code != 200:
            index_list.append(index)
            # print u'error_URL:',index
            # time.sleep(1)
        else:
            article_list = craw_page(res, push_rate)
            # print u'OK_URL:', index
            # time.sleep(0.05)
    content = ''
    for article in article_list:
        data = '[{} push] {}\n{}\n\n'.format(article.get('rate', None), article.get('title', None),
                                             article.get('url', None))
        content += data
    return content


def ptt_hot():
    target_url = 'http://disp.cc/b/PttHot'
    print('Start parsing pttHot....')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""
    for data in soup.select('#list div.row2 div span.listTitle'):
        title = data.text
        link = "http://disp.cc/b/" + data.find('a')['href']
        if data.find('a')['href'] == "796-59l9":
            break
        content += '{}\n{}\n\n'.format(title, link)
    return content


def movie():
    target_url = 'http://www.atmovies.com.tw/movie/next/0/'
    print('Start parsing movie ...')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""
    for index, data in enumerate(soup.select('ul.filmNextListAll a')):
        if index == 20:
            return content
        title = data.text.replace('\t', '').replace('\r', '')
        link = "http://www.atmovies.com.tw" + data['href']
        content += '{}\n{}\n'.format(title, link)
    return content


def technews():
    target_url = 'https://technews.tw/'
    print('Start parsing movie ...')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""

    for index, data in enumerate(soup.select('article div h1.entry-title a')):
        if index == 12:
            return content
        title = data.text
        link = data['href']
        content += '{}\n{}\n\n'.format(title, link)
    return content


def panx():
    target_url = 'https://panx.asia/'
    print('Start parsing ptt hot....')
    rs = requests.session()
    res = rs.get(target_url, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')
    content = ""
    for data in soup.select('div.container div.row div.desc_wrap h2 a'):
        title = data.text
        link = data['href']
        content += '{}\n{}\n\n'.format(title, link)
    return content

#------這裡開始新增--------

def yt_hot():
    res = requests.get("https://www.youtube.com.tw/feed/trending")
    soup = BeautifulSoup(res.text,'html.parser')
    yt_target = 5
    yt_hot = ''
    yt_counter = 0
    # https://www.youtube.com/watch?v=UoSxTDOp6mY
    for a_tag in soup.select('h3'):
        match = re.search(r'.*href="(.*?)" title="(.*?)"',str(a_tag))
        if match:
            yt_counter += 1
            yt_hot += '🌟' + match.group(2) + ' ' + 'https://www.youtube.com' + match.group(1) + '\n'
            # print(match.group(1),match.group(2))
            if yt_counter==yt_target:
                break
    yt_hot = yt_hot[:len(yt_hot)-1]
    return yt_hot


def kkbox_daily():

    kkbox_daily_top = []
    res = requests.get("https://www.kkbox.com/tw/tc/rss/charts-chinese-daily.xml")
    soup = BeautifulSoup(res.text,'html.parser')
    target = 4
    kkbox_daily_top_string = ''
    for index,text in enumerate(soup.find_all('description')):
        if index==1:
            # print(text)
            # pattern = re.compile(r'.*nbsp;')
            # match = pattern.search(str(text))
            match = re.search(r'.*nbsp;(.*?/.*?/.*?)&lt',str(text))
            if match:
                # print(match.group(1))
                kkbox_daily_top.append(' '+str(match.group(1)))

            # findall 匹配多項
            match2 = re.findall(r'.*&gt;(.*?/.*?/.*?)&lt',str(text))
            # if match2:
                # print(match2)

    for i in range(target):
        kkbox_daily_top.append(match2[i])

    for i in kkbox_daily_top:
        kkbox_daily_top_string += '🌟' + i + '\n'

    kkbox_daily_top_string = kkbox_daily_top_string[:len(kkbox_daily_top_string)-1]
    return kkbox_daily_top_string

def invoice():

    res = requests.get("https://bluezz.com.tw")
    soup = BeautifulSoup(res.text,'html.parser')    

    for img in soup.select('img'):
        match = re.search(r'<img alt=.*(https:.*\.jpg)',str(img))
        if match:
            # print(match.group(1))
            return str(match.group(1))


def oricon():
   content = ""
   r = requests.get('https://www.oricon.co.jp/rank/js/d/2017-12-27/') 
   r.encoding='Shift-JIS'
   soup = BeautifulSoup(r.text, 'html.parser')

   for oci in soup.find_all(class_="box-rank-entry"):
      print(oci.find(class_="title").text)
      content += '{}\n{}\n\n'.format(oci.find(class_="name").text,oci.find(class_="title").text)
   return content



#-------以上是新增的--------------------------------
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    print("event.reply_token:", event.reply_token)
    print("event.message.text:", event.message.text)
    if event.message.text == "eyny":
        content = eyny_movie()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "蘋果即時新聞":
        content = apple_news()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "PTT 表特版 近期大於 10 推的文章":
        content = ptt_beauty()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    #if event.message.text == "來張 imgur 正妹圖片":
    #    client = ImgurClient(client_id, client_secret)
    #    images = client.get_album_images(album_id)
    #    index = random.randint(0, len(images) - 1)
    #    url = images[index].link
    #    image_message = ImageSendMessage(
    #        original_content_url=url,
    #        preview_image_url=url
    #   )
    #    line_bot_api.reply_message(
    #       event.reply_token, image_message)
    #    return 0
    #if event.message.text == "隨便來張正妹圖片":
      #  image = requests.get(API_Get_Image)
      #  url = image.json().get('Url')
      #  image_message = ImageSendMessage(
     #       original_content_url=url,
    #        preview_image_url=url
   #     )
  #      line_bot_api.reply_message(
 #           event.reply_token, image_message)
#        return 0
    if event.message.text == "近期熱門廢文":
        content = ptt_hot()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "即時廢文":
        content = ptt_gossiping()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "近期上映電影":
        content = movie()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "科技新報":
        content = technews()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "PanX泛科技":
        content = panx()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "Oricon排行":
        content = oricon()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "kkbox日榜":
        content = kkbox_daily()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0
    if event.message.text == "youtube熱門":
        content = yt_hot()
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=content))
        return 0 
    if event.message.text == "發票":
        content = invoice()
        image_message = ImageSendMessage(
            original_content_url=content,
            preview_image_url=content
        )
        line_bot_api.reply_message(
            event.reply_token,
            image_message)
        return 0                
    if event.message.text == "開始玩":
        buttons_template = TemplateSendMessage(
            alt_text='開始玩 template',
            template=ButtonsTemplate(
                title='選擇服務',
                text='請選擇',
                thumbnail_image_url='https://i.imgur.com/xQF5dZT.jpg',
                actions=[
                    MessageTemplateAction(
                        label='新聞',
                        text='新聞'
                    ),
                    MessageTemplateAction(
                        label='電影',
                        text='電影'
                    ),
                    MessageTemplateAction(
                        label='看廢文',
                        text='看廢文'
                    ),
                    MessageTemplateAction(
                        label='Oricon排行',
                        text='Oricon排行'
                    )
                 #--------------------------
                  
                 #--------------------------   
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
        return 0
    if event.message.text == "新聞":
        buttons_template = TemplateSendMessage(
            alt_text='新聞 template',
            template=ButtonsTemplate(
                title='新聞類型',
                text='請選擇',
                thumbnail_image_url='https://i.imgur.com/vkqbLnz.png',
                actions=[
                    MessageTemplateAction(
                        label='蘋果即時新聞',
                        text='蘋果即時新聞'
                    ),
                    MessageTemplateAction(
                        label='科技新報',
                        text='科技新報'
                    ),
                    MessageTemplateAction(
                        label='PanX泛科技',
                        text='PanX泛科技'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
        return 0
    if event.message.text == "電影":
        buttons_template = TemplateSendMessage(
            alt_text='電影 template',
            template=ButtonsTemplate(
                title='服務類型',
                text='請選擇',
                thumbnail_image_url='https://i.imgur.com/sbOTJt4.png',
                actions=[
                    MessageTemplateAction(
                        label='近期上映電影',
                        text='近期上映電影'
                    ),
                    MessageTemplateAction(
                        label='eyny',
                        text='eyny'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
        return 0
    if event.message.text == "看廢文":
        buttons_template = TemplateSendMessage(
            alt_text='看廢文 template',
            template=ButtonsTemplate(
                title='你媽知道你在看廢文嗎',
                text='請選擇',
                thumbnail_image_url='https://i.imgur.com/ocmxAdS.jpg',
                actions=[
                    MessageTemplateAction(
                        label='近期熱門廢文',
                        text='近期熱門廢文'
                    ),
                    MessageTemplateAction(
                        label='即時廢文',
                        text='即時廢文'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
        return 0
    if event.message.text == "正妹":
        buttons_template = TemplateSendMessage(
            alt_text='正妹 template',
            template=ButtonsTemplate(
                title='選擇服務',
                text='請選擇',
                thumbnail_image_url='https://i.imgur.com/qKkE2bj.jpg',
                actions=[
                    MessageTemplateAction(
                        label='PTT 表特版 近期大於 10 推的文章',
                        text='PTT 表特版 近期大於 10 推的文章'
                    ),
                    MessageTemplateAction(
                        label='來張 imgur 正妹圖片',
                        text='來張 imgur 正妹圖片'
                    ),
                    MessageTemplateAction(
                        label='隨便來張正妹圖片',
                        text='隨便來張正妹圖片'
                    )
                ]
            )
        )
        line_bot_api.reply_message(event.reply_token, buttons_template)
        return 0
#---------------------------------------------------

#-------------------------------------------------------
    buttons_template = TemplateSendMessage(
        alt_text='目錄 template',
        template=ButtonsTemplate(
            title='選擇服務',
            text='請選擇',
            thumbnail_image_url='https://i.imgur.com/QxR8tQh.jpg',
            actions=[
                MessageTemplateAction(
                    label='開始玩',
                    text='開始玩'
                ),
                URITemplateAction(
                    label='影片介紹 阿肥bot',
                    uri='https://youtu.be/1IxtWgWxtlE'
                ),
                URITemplateAction(
                    label='如何建立自己的 Line Bot',
                    uri='https://github.com/twtrubiks/line-bot-tutorial'
                ),
                URITemplateAction(
                    label='聯絡作者',
                    uri='https://www.facebook.com/TWTRubiks?ref=bookmarks'
                )
            ]
        )
    )
    line_bot_api.reply_message(event.reply_token, buttons_template)


if __name__ == '__main__':
    context = ('/home/jc0424057/line-bot-tutorial-master/cert/certificate.crt', '/home/jc0424057/line-bot-tutorial-master/cert/private.key')
    app.run(host='linebot.nkfuststudents.cf', port=443, ssl_context=context, threaded=True, debug=True)
  #  app.run()
