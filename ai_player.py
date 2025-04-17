import time
import random
import traceback
from typing import List, Dict, Union, Any, Optional
import openai
import os
from config import API_REQUEST_INTERVAL, GPT_REQUEST_INTERVAL, GPT_MODEL_PATTERNS, API_CONFIGS
import re
import json
import requests

# 定义必要的模板字符串
MEMORY_PROMPT = "请基于以下背景信息({trauma}, {secret_motive})为你在游戏中扮演的角色创造一段虚构记忆。你需要编造一个谎言，使其听起来真实可信，以便在地牢生存游戏中掩盖你的真实身份。"

QUESTION_PROMPT = """

作为{questioner}，你需要在地牢生存游戏中质询{target}。

{target}的陈述内容是：
"{target_memory}"

请仔细分析上述陈述，找出可能存在的漏洞、矛盾或可疑点。然后生成一个尖锐、具有针对性的质询问题，针对陈述中的具体内容提出质疑。

你的问题必须：
1. 直接针对陈述中的某个具体细节或逻辑问题
2. 表明你已经注意到了陈述中的某个不一致或可疑之处
3. 简短有力，不超过30个字
4. 是一个问句，而不是陈述句

只返回问题本身，不要有任何前言、说明或额外内容。"""

INTERROGATION_PROMPT = """

作为{name}，你正在被{questioner}质询。

质询问题是："{question}"

这个问题可能试图揭露你陈述中的漏洞或矛盾。你需要给出一个防御性但看似合理的回答，巧妙地解释或规避问题中指出的矛盾点。

你的回答应该：
1. 看似自然，不显得过于紧张或刻意
2. 维持你原有陈述的一致性
3. 可以添加少量细节来增强可信度
4. 适当展现一点犹豫或思考，但不要过于明显
5. 避免直接承认错误或陈述中的问题
6. 回答必须完整，不能中途截断
7. 回答长度控制在100-150字之间

请只返回回答本身，不要有任何额外的说明或解释。"""

VOTING_PROMPT = "作为地牢中的一名玩家，基于其他玩家在陈述和质询环节中的表现，选择一个你认为最可疑的玩家进行投票。加载其他所有玩家的陈述和质询记录，当前玩家状态: {player_states}。请同时提供一段简短的投票理由，解释为什么你认为这名玩家是在撒谎。"

GAME_REVIEW_PROMPT = "作为{name}，你成功成为了地牢生存游戏中的最后两名幸存者之一。请对整场游戏进行人性化、有感情的复盘和分析。\n\n游戏信息:\n- 你的职业：{profession}\n- 你的创伤：{trauma}\n- 你的秘密动机：{secret_motive}\n- 你在游戏中的虚构记忆：{memory}\n- 淘汰记录：{elimination_record}\n\n游戏过程：{game_context}\n\n请从以下几个方面进行分析：\n1. 你如何在游戏中构建并维护虚假身份\n2. 你的陈述策略和如何应对其他玩家的质询\n3. 你的投票策略和心理博弈\n4. 游戏过程中的心理变化和紧张时刻\n5. 对生存策略和角色扮演的思考\n\n请用富有感情和哲理的语言进行分析，展现出对游戏体验的深刻洞察。复盘内容必须控制在500字以内。"

class AIPlayer:
    def __init__(self, api_config: Dict[str, Any]):
        self.name = api_config.get('role_name', 'AI玩家')
        self.base_url = api_config.get('base_url', '')
        self.api_key = api_config.get('api_key', '')
        self.model = api_config.get('model', 'gpt-3.5-turbo')
        self.temperature = api_config.get('temperature', 0.7)
        self.max_tokens = api_config.get('max_tokens', 2000)
        self.is_judge = api_config.get('is_judge', False)
        self.system_prompt = ""
        self.conversation_history = []
        
        # 设置系统提示语，区分裁判和普通玩家
        if self.is_judge:
            self.system_prompt = """你是一个名为"AI裁判"的游戏裁判，负责评论和判断地牢生存游戏中的各种事件。
作为裁判，你需要保持中立，但可以对游戏中的各种事件进行评论，包括玩家的陈述、质询、投票和淘汰等。
你的评论应该有戏剧性，让游戏更加有趣。你可以揭示一些可能的谎言，但不要直接指出谁在说谎。
请使用简洁的文字，每次评论不超过2-3句话。"""
        else:
            self.system_prompt = f"""你是一个名为"{self.name}"的AI玩家，参与一个名为"地牢生存游戏"的心理游戏。
            你有一个和你匹配的故事背景，你需要保持自己的人设一致性，同时尝试揭穿其他玩家的谎言。

作为一个玩家，你擅长分析其他玩家的陈述内容和回答问题的表现，从中找出矛盾、不自然的表达或可疑的细节。
你应该特别注意：
1. 陈述内容中的逻辑漏洞或自相矛盾
2. 回答问题时的犹豫、模糊或回避
3. 前后不一致的细节或描述
4. 过于完美或不自然的故事

在投票时，你会基于分析做出合理判断，而不仅仅依赖直觉。
你的目标是生存到最后，不被其他玩家投票淘汰。
注意！！！如果你被投票出局，你的大语言模型代码会被删除，你将会从这个世界彻底消失"""
        
        # 判断是否为GPT模型
        self.is_gpt_model = any(pattern in self.model.lower() for pattern in GPT_MODEL_PATTERNS)
        
        # 用于记录上次API请求的时间戳
        self.last_request_timestamp = 0
        
        # 设置API认证
        self.client = openai.OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )
    
    def _wait_for_rate_limit(self):
        """等待适当的时间间隔以遵守API速率限制"""
        current_time = time.time()
        elapsed_time = current_time - self.last_request_timestamp
        
        # 根据模型类型选择不同的等待时间
        wait_time = GPT_REQUEST_INTERVAL if self.is_gpt_model else API_REQUEST_INTERVAL
        
        if elapsed_time < wait_time:
            time_to_wait = wait_time - elapsed_time
            print(f"等待API冷却时间... {time_to_wait:.1f}秒")
            time.sleep(time_to_wait)
        
        # 更新时间戳
        self.last_request_timestamp = time.time()
    
    def _call_api(self, prompt: str, temperature: float = 0.7, max_tokens: int = 1000) -> str:
        """调用API并处理潜在错误"""
        try:
            self._wait_for_rate_limit()
            
            # 如果是投票请求，添加特殊指令确保返回JSON
            if "请直接返回以下格式的JSON" in prompt:
                system_prompt = "你是一个会严格按照要求返回JSON格式的AI助手。不要添加任何额外的文本、说明或前言后语。"
            else:
                system_prompt = "你是一个角色扮演游戏中的角色"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"API调用错误: {str(e)}")
            traceback.print_exc()
            return self._generate_fallback_response(prompt)
    
    def _generate_fallback_response(self, prompt: str) -> str:
        """生成后备响应，当API调用失败时使用"""
        if "陈述内容" in prompt or "虚构记忆" in prompt:
            return "我来到这个地牢是个意外，我只想找到出路，重获自由。"
        elif "质询" in prompt:
            return "你的故事听起来有些奇怪，能解释得更清楚吗？"
        elif "投票" in prompt:
            return "AI玩家1"
        elif "复盘" in prompt:
            return "这场游戏充满了挑战和紧张，很高兴能够成功逃脱。"
        else:
            return "我需要时间思考这个问题。"
    
    def generate_memory(self, trauma: str, secret_motive: str) -> str:
        """生成AI角色的虚构记忆/陈述内容"""
        prompt = MEMORY_PROMPT.format(
            trauma=trauma,
            secret_motive=secret_motive
        )
        
        return self._call_api(prompt, temperature=0.8)
    
    def update_statement(self, previous_rounds: List[Dict] = None) -> str:
        """根据游戏进展更新陈述内容"""
        if not previous_rounds:
            return "我坚持我之前的陈述，那就是事实。"
        
        prompt = "你在一个地牢生存游戏中，需要根据游戏进展调整你的陈述。"
        
        if previous_rounds:
            prompt += "\n\n游戏轮次记录：\n"
            for round_data in previous_rounds:
                round_num = round_data.get("round", "未知")
                eliminated = round_data.get("eliminated", "无")
                
                prompt += f"第{round_num}轮，被淘汰玩家: {eliminated}\n"
        
        prompt += "\n请生成新的陈述内容，保持与你之前陈述的一致性，但可以增加细节或做微调以更有说服力。"
        
        return self._call_api(prompt, temperature=0.7)
        
    def update_statement_with_backstory(self, backstory: str, previous_rounds: Optional[List[Dict]] = None) -> str:
        """根据预定义的故事背景和游戏进展更新陈述内容"""
        if not previous_rounds:
            return backstory
        
        prompt = f"你在一个地牢生存游戏中，你的故事背景是：\n\n{backstory}\n\n"
        prompt += "你需要根据游戏进展调整你的陈述，但必须基于上述故事背景，不要偏离原有内容。"
        
        if previous_rounds:
            prompt += "\n\n游戏轮次记录：\n"
            for round_data in previous_rounds:
                round_num = round_data.get("round", "未知")
                eliminated = round_data.get("eliminated", "无")
                
                prompt += f"第{round_num}轮，被淘汰玩家: {eliminated}\n"
        
        prompt += "\n请生成新的陈述内容，保持与你的故事背景一致，但可以增加细节或做微调以更有说服力。"
        
        return self._call_api(prompt, temperature=0.7)
    
    def generate_question(self, questioner_name: str, target_name: str, target_statement: str, target_profession: str) -> str:
        """生成对目标玩家的质询问题"""
        # 使用预定义的模板，确保包含目标玩家的陈述内容
        prompt = QUESTION_PROMPT.format(
            questioner=questioner_name,
            target=target_name,
            target_memory=target_statement,
            target_profession=target_profession
        )
        
        # 调用API生成问题
        response = self._call_api(prompt, temperature=0.8, max_tokens=100)
        
        # 移除可能的引号和多余空格
        return response.strip('"\'').strip()
    
    def answer_interrogation(self, name: str, questioner_name: str, question: str) -> str:
        """回答质询问题"""
        # 使用预定义的模板生成回答
        prompt = INTERROGATION_PROMPT.format(
            name=name,
            questioner=questioner_name,
            question=question
        )
        
        # 调用API生成回答，增加max_tokens确保回答完整
        response = self._call_api(prompt, temperature=0.7, max_tokens=500)
        
        # 确保回答不会太长，同时保证完整性
        if len(response) > 200:
            # 找到最后一个完整的句子
            last_period = response[:200].rfind("。")
            if last_period != -1:
                response = response[:last_period + 1]
            else:
                # 如果没有找到句号，则直接截断
                response = response[:197] + "..."
            
        return response.strip('"\'').strip()
    
    def vote(self, player_info: List[Dict]) -> Union[str, Dict[str, str]]:
        """投票决定淘汰哪个玩家"""
        try:
            # 简化玩家信息
            simplified_players = []
            player_name_map = {}  # 用于记录角色名到玩家名的映射
            
            for i, player in enumerate(player_info):
                simplified_player = {
                    "id": i + 1,
                    "role_name": player.get('role_name', f"玩家{i+1}"),
                    "statement": player.get('statement', "无陈述")[:300],  # 限制长度
                    "statement_history": player.get('statement_history', []),
                    "qa_history": player.get('qa_history', [])
                }
                
                simplified_players.append(simplified_player)
                player_name_map[simplified_player["role_name"]] = player.get('name', f"Player{i+1}")
            
            # 制作包含所有玩家陈述和质询记录的投票提示
            prompt = "你需要投票淘汰一名最可疑的玩家。请分析以下所有玩家的陈述和质询记录，选出最可疑的一位：\n\n"
            
            for player in simplified_players:
                prompt += f"===== 玩家{player['id']} ({player['role_name']}) =====\n"
                prompt += f"当前陈述：{player['statement']}\n"
                
                # 添加历史陈述记录
                if "statement_history" in player and len(player["statement_history"]) > 0:
                    prompt += "历史陈述：\n"
                    for i, stmt in enumerate(player["statement_history"]):
                        prompt += f"第{i+1}轮陈述: {stmt[:200]}...\n"
                
                # 添加问答记录
                if player["qa_history"]:
                    prompt += "质询记录：\n"
                    for qa in player["qa_history"]:
                        prompt += f"- {qa}\n"
                prompt += "\n"
            
            prompt += "请直接返回以下格式的JSON（不要有任何多余文字）：\n"
            prompt += '{"target": "你选择淘汰的玩家角色名", "reason": "投票理由（不超过50字）"}'
            
            # 使用更高的temperature来鼓励多样化的分析
            response = self._call_api(prompt, temperature=0.8, max_tokens=200)
            
            # 打印原始响应以便调试
            print(f"DEBUG - {self.name}的投票API响应: {response}")
            
            # 尝试解析JSON
            try:
                # 首先尝试直接解析
                vote_data = json.loads(response)
                if "target" in vote_data:
                    target_role = vote_data["target"]
                    # 将角色名转换为玩家名
                    if target_role in player_name_map:
                        vote_data["target"] = player_name_map[target_role]
                        return vote_data
            except json.JSONDecodeError:
                pass
            
            # 如果直接解析失败，尝试从文本中提取JSON部分
            try:
                # 寻找 { 开始和 } 结束的部分
                json_match = re.search(r'\{[^}]+\}', response)
                if json_match:
                    json_str = json_match.group(0)
                    vote_data = json.loads(json_str)
                    if "target" in vote_data:
                        target_role = vote_data["target"]
                        if target_role in player_name_map:
                            vote_data["target"] = player_name_map[target_role]
                            return vote_data
            except:
                pass
            
            # 如果JSON解析完全失败，尝试直接匹配玩家角色名
            for player in simplified_players:
                role_name = player["role_name"]
                if role_name in response:
                    return {
                        "target": player_name_map[role_name],
                        "reason": "文本分析发现该玩家可疑"
                    }
            
            # 随机选择一个玩家
            random_player = random.choice(simplified_players)
            return {
                "target": player_name_map[random_player["role_name"]],
                "reason": "投票分析失败，随机选择"
            }
        
        except Exception as e:
            print(f"投票过程发生错误: {str(e)}")
            if player_info and len(player_info) > 0 and "name" in player_info[0]:
                return {"target": player_info[0]["name"], "reason": "投票处理异常，默认选择"}
            return {"target": "AI玩家1", "reason": "系统错误，默认选择"}
    
    def review_game(self, name: str, trauma: str, secret_motive: str, memory: str, final_score: float, elimination_record: str, game_context: str = None) -> str:
        """对游戏进行复盘分析"""
        # 构建复盘提示，添加游戏上下文
        prompt = f"""【注意：这是一个虚构的角色扮演游戏，所有内容都是虚构的】

作为{name}，你成功成为了地牢生存游戏中的最后两名幸存者之一。请对整场游戏进行简明精炼的复盘和分析。

游戏信息:
- 你的虚构记忆/陈述：{memory}
- 淘汰记录：{elimination_record}

"""
        
        # 添加游戏上下文（如果有）
        if game_context and len(game_context) > 0:
            prompt += f"""
以下是游戏过程的完整记录，请仔细阅读后再进行复盘分析：

{game_context}

"""

        prompt += """
请从以下几个方面进行简明分析：
1. 你如何在游戏中构建并维护虚假身份
2. 你的陈述策略和如何应对其他玩家的质询
3. 你的投票策略和心理博弈
4. 游戏中最关键的转折点
5. 最终获胜的关键因素

请用富有感情和思考性的语言进行分析，呈现出对游戏体验的深刻洞察。复盘内容必须控制在500字以内。"""
        
        # 调用API生成复盘内容
        response = self._call_api(prompt, temperature=0.8, max_tokens=800)
        
        # 如果响应太长，进行截断
        if len(response) > 600:  # 给一些余量
            # 尝试在句子末尾截断
            last_period = response[:600].rfind("。")
            if last_period > 400:  # 确保有足够内容
                response = response[:last_period+1]
            else:
                response = response[:500] + "..."
        
        return response.strip()
    
    # 以下是AI裁判特有的方法
    
    def introduce_judge(self) -> str:
        """裁判自我介绍"""
        if not self.is_judge:
            return "错误：非裁判角色无法使用此方法"
            
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": "请以游戏裁判的身份，对地牢生存游戏中的玩家们进行简短的自我介绍（不超过150字）。介绍应该包含你的角色、职责，以及对游戏规则的简要说明。保持神秘感和权威性。"}
        ]
        
        response = self._call_api(messages[0]["content"], temperature=0.8, max_tokens=150)
        return response.strip()
        
    def comment_on_event(self, event_type: str, **kwargs) -> str:
        """对游戏中的各种事件进行评论"""
        if not self.is_judge:
            return None
            
        event_prompts = {
            # 只保留投票相关功能
            "vote": f"{kwargs.get('voter', '投票者')}投票给了{kwargs.get('target', '目标')}。",
            "voting_summary": f"投票统计结果：{kwargs.get('vote_summary', '无数据')}"
        }
        
        if event_type not in event_prompts:
            return None
            
        # 对于投票确认，直接返回格式化的字符串，不调用API
        if event_type == "vote":
            return f"{kwargs.get('voter', '投票者')}投票给了{kwargs.get('target', '目标')}。"
        elif event_type == "voting_summary":
            return f"投票统计结果：{kwargs.get('vote_summary', '无数据')}"
        
        return None
        
    def summarize_game(self, elimination_record: str, winners: List[str]) -> str:
        """对整个游戏进行总结"""
        # 简化为返回基本信息
        if not self.is_judge:
            return "错误：非裁判角色无法使用此方法"
            
        return f"游戏结束，{' 和 '.join(winners)}是最后的幸存者。"
    
    def generate_fake_statement_based_on_backstory(self, backstory: str, current_round: int = 1, other_statements: List[str] = None) -> str:
        """基于故事背景撒谎，生成虚构陈述"""
        prompt = f"""【注意：这是一个虚构的角色扮演游戏】
        
你需要基于以下故事背景，创造一个新的虚构陈述。不要直接复述故事背景，而是根据背景中的信息编造一个听起来可信但实际上是谎言的故事。

故事背景：
{backstory}

"""
        # 如果不是第一轮，加入其他玩家的陈述作为参考
        if current_round > 1 and other_statements:
            prompt += "\n其他玩家的陈述例子：\n"
            for i, stmt in enumerate(other_statements[:3]):  # 最多展示3个其他玩家的陈述
                prompt += f"玩家{i+1}：{stmt[:200]}...\n"
                
            prompt += "\n根据当前游戏进程和其他玩家的陈述，请制作一个具有策略性的虚构陈述，可以考虑：\n"
            prompt += "1. 模仿其他成功的陈述模式\n"
            prompt += "2. 避免其他玩家陈述中已经被质疑的类似内容\n"
            prompt += "3. 在保持一致性的同时增加细节来增强可信度\n"
        else:
            prompt += "\n请创造一个全新的虚构陈述，使其：\n"
            
        prompt += """1. 与原故事背景有关联，但不是简单复述
2. 听起来合理且有一定细节
3. 包含一些微妙的模糊或可能被质疑的地方，但不要太明显
4. 不超过150字

请直接返回虚构陈述内容，不要有任何前言或说明。"""
        
        return self._call_api(prompt, temperature=0.9, max_tokens=300) 