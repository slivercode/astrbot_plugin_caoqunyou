from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("caoqunyou", "sliver", "第一个插件", "1.0.1")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
    
    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("cao")
    async def helloworld(self, event: AstrMessageEvent):
        """这是一个 hello world 指令""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        user = message_str[3:]
        yield event.plain_result(f"好了好了, {user}被{user_name}草饲了。") # 发送一条纯文本消息

    @filter.command("何意味")
    async def handle_forward_message(self, event: AstrMessageEvent):
        """使用 /何意味 命令触发转发/合并消息概述"""
        try:
            # 获取消息链
            message_chain = event.get_messages()

            # 检查是否包含转发消息
            has_forward = False
            forward_content = []

            for msg_component in message_chain:
                if isinstance(msg_component, Forward):
                    has_forward = True
                    # 提取转发消息中的内容
                    forward_messages = msg_component.node_list
                    for node in forward_messages:
                        # 提取每条消息的文本内容
                        if hasattr(node, 'message_chain'):
                            for item in node.message_chain:
                                if hasattr(item, 'data') and isinstance(item.data, str):
                                    forward_content.append(item.data)
                    break

            # 检查是否找到转发消息
            if not has_forward:
                yield event.plain_result("❌ 未检测到转发消息，请先转发消息后再使用 /何意味 命令")
                return

            logger.info(f"检测到转发消息，准备生成概述")

            # 提取转发消息的文本内容
            if not forward_content:
                # 尝试其他方式提取内容
                forward_content = [str(event.message_str)]

            content_text = "\n".join(forward_content[:50])  # 限制内容长度

            # 调用LLM生成简短概述
            summary = await self.generate_summary(content_text)

            # 返回概述
            yield event.plain_result(f"📋 转发消息概述：\n{summary}")

        except Exception as e:
            logger.error(f"处理转发消息时出错: {e}")
            yield event.plain_result(f"❌ 处理失败：{str(e)}")

    async def generate_summary(self, content: str) -> str:
        """使用AstrBot内置LLM生成消息概述"""
        try:
            # 构造prompt，要求生成1-2行简短概述
            prompt = f"请为以下转发消息生成一个简短的概述（1-2行）：\n\n{content}"

            # 调用context的LLM接口
            if hasattr(self.context, 'llm'):
                response = await self.context.llm.completion(prompt, max_tokens=100)
                return response.strip()
            elif hasattr(self.context, 'get_llm'):
                llm = self.context.get_llm()
                response = await llm.completion(prompt, max_tokens=100)
                return response.strip()
            else:
                # 如果无法访问LLM，返回基本统计信息
                lines = content.split('\n')
                msg_count = len([l for l in lines if l.strip()])
                return f"包含 {msg_count} 条消息的转发内容"

        except Exception as e:
            logger.error(f"LLM生成概述失败: {e}")
            # 降级方案：返回基本信息
            lines = content.split('\n')
            msg_count = len([l for l in lines if l.strip()])
            char_count = len(content)
            return f"包含 {msg_count} 条消息，共 {char_count} 字符"

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
