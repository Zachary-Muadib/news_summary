import os, requests, plugins
from datetime import datetime
from plugins import Plugin, Event, EventContext, EventAction
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType

@plugins.register(name="NewsSummary", desc="Responds to '汇总今天的新闻'", version="1.0", author="YourName", desire_priority=0)
class NewsSummary(Plugin):
    def __init__(self):
        super().__init__()
        self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
        self.handlers[Event.ON_DECORATE_REPLY] = self.on_decorate_reply  # 新增处理装饰回复的事件
        self.news_cache_file = "news_summary_cache.txt"
        self.last_update_date = self.check_and_load_cache()
        self.should_save_output = False

    def on_handle_context(self, e_context: EventContext):
        context = e_context['context']
        today = datetime.now().strftime("%Y-%m-%d")

        if context.type == ContextType.TEXT and "汇总今天的新闻" in context.content:
            # 检查是否已有今天的新闻摘要缓存
            if self.last_update_date == today and os.path.exists(self.news_cache_file):
                with open(self.news_cache_file, "r", encoding="utf-8") as file:
                    _ = file.readline()  # 读取并忽略第一行（日期）
                    cached_news = file.read()
                e_context['reply'] = Reply(ReplyType.TEXT, cached_news)
                e_context.action = EventAction.BREAK_PASS
            else:
                # 没有缓存，或缓存不是今天的，需要重新获取新闻摘要
                news = self.get_news_summary()
                if news:
                    updated_request = f"{context.content}\n\n---\n[请求处理完成]以下是今天的新闻:\n{news}\n---\n"
                    context.content = updated_request
                    self.last_update_date = today
                    self.should_save_output = True  # 设置标记为True
                    e_context.action = EventAction.CONTINUE
                else:
                    e_context['reply'] = Reply(ReplyType.TEXT, "无法获取新闻摘要。")
                    e_context.action = EventAction.BREAK_PASS
        else:
            e_context.action = EventAction.CONTINUE

    # 新增方法来处理装饰回复事件
    def on_decorate_reply(self, e_context: EventContext):
        if self.should_save_output:
            reply = e_context['reply']
            if reply and reply.type == ReplyType.TEXT:
                self.save_news_cache(reply.content)
            self.should_save_output = False  # 重置标记为False

    def check_and_load_cache(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if os.path.exists(self.news_cache_file):
            with open(self.news_cache_file, "r", encoding="utf-8") as file:
                first_line = file.readline().strip()
                if today == first_line:
                    return today
                else:
                    return ""
            # 确保在文件不存在当日日期时返回空字符串
        return ""

    def save_news_cache(self, gpt_output):
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            with open(self.news_cache_file, "w", encoding="utf-8") as file:
                file.write(f"{today}\n{gpt_output}")
        except Exception as e:
            print(f"Error saving news summary to cache: {e}")

    def get_news_summary(self):
        url = "http://114.132.200.184:5000/get_report"
        params = {"token": "123"}
        try:
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                return data.get('report', '新闻摘要不可用。')
            else:
                return "获取新闻摘要失败，响应状态码：{}".format(response.status_code)
        except requests.RequestException as e:
            return "请求新闻摘要时发生错误：{}".format(e)
