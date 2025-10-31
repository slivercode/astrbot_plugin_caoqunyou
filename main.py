from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp


@register("helloworld", "YourName", "一个简单的 Hello World 插件", "1.0.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`

    # 注册 /何意味 指令，处理引用别人转发的消息
    @filter.command("何意味")
    async def heyiwei(self, event: AstrMessageEvent):
        """使用 /何意味 命令触发引用转发消息的概述"""
        try:
            # 获取消息对象
            message_obj = event.message_obj

            reply_content = []
            has_reply = False
            has_forward_in_reply = False

            # 第一步：查找 Reply 消息段（引用消息）
            for component in message_obj.message:
                if isinstance(component, Comp.Reply):
                    has_reply = True
                    replied_message_id = component.id
                    logger.info(f"检测到引用消息，ID: {replied_message_id}")

                    # 尝试从 Reply 组件中获取被引用的消息内容
                    # Reply 组件可能包含被引用消息的部分信息
                    if hasattr(component, 'message'):
                        # 检查被引用的消息是否包含转发内容
                        reply_message = component.message if isinstance(component.message, list) else [
                            component.message]
                        for reply_item in reply_message:
                            if isinstance(reply_item, Comp.Forward):
                                has_forward_in_reply = True
                                logger.info("被引用的消息包含转发内容")
                                # 提取转发消息中的内容
                                forward_messages = reply_item.node_list
                                for node in forward_messages:
                                    if hasattr(node, 'message_chain'):
                                        for item in node.message_chain:
                                            if hasattr(item, 'data') and isinstance(item.data, str):
                                                reply_content.append(item.data)
                                            elif hasattr(item, 'text'):
                                                reply_content.append(item.text)
                    break

            # 第二步：如果当前消息本身包含转发（没有引用的情况）
            if not has_reply:
                for component in message_obj.message:
                    if isinstance(component, Comp.Forward):
                        has_forward_in_reply = True
                        logger.info("当前消息包含转发内容")
                        forward_messages = component.node_list
                        for node in forward_messages:
                            if hasattr(node, 'message_chain'):
                                for item in node.message_chain:
                                    if hasattr(item, 'data') and isinstance(item.data, str):
                                        reply_content.append(item.data)
                                    elif hasattr(item, 'text'):
                                        reply_content.append(item.text)
                        break

            # 检查是否找到引用或转发消息
            if not has_reply and not has_forward_in_reply:
                yield event.plain_result(
                    "❌ 未检测到引用或转发消息\n💡 使用方法：回复/引用别人发送的转发消息，然后发送 /何意味 命令")
                return

            # 如果找到了引用但没有提取到转发内容
            if has_reply and not reply_content:
                # 尝试获取消息的原始内容
                # 注意：某些平台可能不提供完整的被引用消息内容
                yield event.plain_result(
                    "❌ 无法获取被引用消息的转发内容\n💡 提示：\n1. 请确保回复的是转发消息\n2. 某些平台可能不支持获取引用消息的完整内容\n3. 可以直接转发消息后使用 /何意味 命令")
                return

            logger.info(f"成功提取到 {len(reply_content)} 条消息内容")

            # 合并内容
            content_text = "\n".join(reply_content[:100])  # 限制内容长度，最多100条

            if not content_text.strip():
                yield event.plain_result("❌ 提取的消息内容为空")
                return

            # 调用LLM生成简短概述
            logger.info("开始生成消息概述")
            summary = await self.generate_summary(content_text)

            # 返回概述
            msg_count = len(reply_content)
            yield event.plain_result(f"📋 转发消息概述（共{msg_count}条）：\n\n{summary}")

        except Exception as e:
            logger.error(f"处理消息时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            yield event.plain_result(f"❌ 处理失败：{str(e)}\n\n请查看日志获取详细错误信息")

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
