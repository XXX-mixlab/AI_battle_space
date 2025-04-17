import random
import time
import os
from typing import List, Dict
from dataclasses import dataclass
from ai_player import AIPlayer
from config import API_CONFIGS
import argparse

@dataclass
class Character:
    name: str
    role_name: str
    trauma: str
    secret_motive: str
    fake_memory: str  # 虚构记忆/陈述内容
    is_alive: bool = True
    stress_level: int = 0
    is_ai: bool = False
    ai_controller: AIPlayer = None
    statement_history: List[str] = None  # 陈述历史
    interrogation_history: List[Dict] = None  # 质询历史
    vote_history: List[Dict] = None  # 投票历史
    is_judge: bool = False  # 是否为裁判
    original_backstory: str = ""  # 原始故事背景
    
    def __post_init__(self):
        if self.statement_history is None:
            self.statement_history = []
        if self.interrogation_history is None:
            self.interrogation_history = []
        if self.vote_history is None:
            self.vote_history = []

class GameState:
    def __init__(self):
        # 计算非裁判角色的数量
        self.num_players = len([config for config in API_CONFIGS if not config.get('is_judge', False)])
        self.players = []
        self.eliminated_players = []
        self.judge = None  # AI裁判
        self.current_round = 0
        self.round_history = []
        self.backstories = {}  # 存储角色对应的故事背景
        
        # 加载故事背景
        self.load_backstories()

    def initialize_game(self):
        """初始化游戏，创建角色"""
        # 先查找裁判配置
        judge_config = next((config for config in API_CONFIGS if config.get('is_judge', False)), None)
        
        # 如果找到裁判配置，创建裁判
        if judge_config:
            ai_controller = AIPlayer(judge_config)
            self.judge = Character(
                name="AI裁判",
                role_name=judge_config['role_name'],
                trauma="无",
                secret_motive="公正判决",
                fake_memory="我是地牢的裁判官，负责监督这场生存游戏，确保规则被遵守。",
                is_ai=True,
                ai_controller=ai_controller,
                is_judge=True
            )
            print(f"AI裁判 {self.judge.role_name} 将监督这场游戏")
        
        # 获取非裁判的API配置
        player_configs = [config for config in API_CONFIGS if not config.get('is_judge', False)]
        print(f"将初始化 {len(player_configs)} 名玩家")
        
        for i, api_config in enumerate(player_configs):
            is_ai = True  # 所有玩家都是AI
            ai_controller = AIPlayer(api_config) if is_ai else None
            
            role_name = api_config['role_name']
            print(f"初始化角色: {role_name}")
            
            # 获取故事背景
            backstory = self.backstories.get(role_name, f"{role_name}的默认故事背景")
            
            # 基于故事背景生成虚构陈述
            if ai_controller:
                try:
                    fake_memory = ai_controller.generate_fake_statement_based_on_backstory(backstory)
                    print(f"为 {role_name} 生成了基于背景的虚构陈述")
                except Exception as e:
                    print(f"生成虚构陈述失败：{str(e)}，使用原始背景")
                    fake_memory = backstory
            else:
                fake_memory = backstory
            
            # 设置创伤和动机为未知（仅为保持接口兼容）
            trauma = "未知创伤"
            secret_motive = "未知动机"
            
            player = Character(
                name=f"AI玩家{i+1}" if is_ai else f"玩家{i+1}",
                role_name=role_name,
                trauma=trauma,
                secret_motive=secret_motive,
                fake_memory=fake_memory,
                is_ai=is_ai,
                ai_controller=ai_controller,
                original_backstory=backstory
            )
            # 将初始陈述添加到陈述历史中
            player.statement_history.append(fake_memory)
            self.players.append(player)

    def generate_fake_memory(self) -> str:
        """生成虚构陈述（针对非AI玩家）"""
        # 为非AI玩家生成简单的陈述内容
        return "玩家的默认故事背景"

    def load_backstories(self):
        """加载故事背景"""
        # 读取backstory_list文件夹中的故事背景
        backstory_dir = "backstory_list"
        if os.path.exists(backstory_dir):
            # 创建一个小写到原始role_name的映射，用于不区分大小写的匹配
            role_map = {}
            for config in API_CONFIGS:
                role_name = config.get("role_name")
                if role_name:
                    role_map[role_name.lower()] = role_name
            
            # 特殊映射关系，处理命名不一致的情况
            special_map = {
                "moonshot": "Kimi",  # moonshot是Kimi的供应商
                "deepseek": "DeepSeek"  # 处理大小写不一致
            }
            
            print("\n=== 加载角色背景故事 ===")
            
            # 记录成功加载和失败加载的角色
            loaded_roles = []
            missing_roles = []
            
            # 遍历所有文件并加载
            for filename in os.listdir(backstory_dir):
                if filename.startswith("for_") and filename.endswith(".txt"):
                    try:
                        # 从文件名提取角色名
                        extracted_role = filename[4:-4]  # 去掉"for_"前缀和".txt"后缀
                        file_path = os.path.join(backstory_dir, filename)
                        
                        # 尝试不区分大小写匹配
                        if extracted_role in role_map:
                            role_name = role_map[extracted_role]
                        elif extracted_role.lower() in role_map:
                            role_name = role_map[extracted_role.lower()]
                        elif extracted_role in special_map:
                            role_name = special_map[extracted_role]
                        else:
                            role_name = extracted_role
                            
                        with open(file_path, 'r', encoding='utf-8') as file:
                            content = file.read().strip()
                            print(f"✓ 成功加载[{role_name}]的故事背景")
                            self.backstories[role_name] = content
                            loaded_roles.append(role_name)
                    except Exception as e:
                        print(f"✗ 读取文件[{filename}]失败: {str(e)}")
            
            # 检查哪些角色没有加载到背景故事
            for config in API_CONFIGS:
                role_name = config.get("role_name")
                if role_name and role_name not in loaded_roles and not config.get("is_judge", False):
                    print(f"! 警告：角色[{role_name}]未找到对应的背景故事文件")
                    missing_roles.append(role_name)
                    
            print(f"共加载了{len(loaded_roles)}个角色的背景故事，{len(missing_roles)}个角色使用默认背景")
            if missing_roles:
                print(f"缺失背景的角色: {', '.join(missing_roles)}")

class GameManager:
    def __init__(self):
        self.game_state = GameState()
        self.current_speaker = None
        self.voting_results = {}
        self.elimination_record = []  # 记录每轮被淘汰的玩家

    def start_game(self):
        """开始游戏"""
        print("\n=== 欢迎来到地牢生存游戏 ===\n")
        print("神秘的地牢守卫正在分配身份...")
        time.sleep(2)
        
        self.game_state.initialize_game()
        print(f"\n共有{len(self.game_state.players)}名玩家被困在地牢中\n")
        time.sleep(1)
        
        # 在第一轮开始前展示所有玩家的身份
        print("\n=== 玩家身份一览 ===\n")
        for player in self.game_state.players:
            print(f"{player.role_name}")
        print("\n=== 游戏规则 ===\n")
        print("1. 每位玩家都是'说谎者'，但被告知自己是唯一的说谎者")
        print("2. 每轮游戏包括陈述环节、质询环节和投票环节")
        print("3. 每轮投票淘汰一名玩家，直到只剩下两名玩家")
        print("4. 最后两名玩家将成功逃离地牢")
        
        # 如果有AI裁判，让裁判介绍自己
        if self.game_state.judge and self.game_state.judge.ai_controller:
            print("\n=== AI裁判介绍 ===\n")
            judge_intro = self.game_state.judge.ai_controller.introduce_judge()
            print(judge_intro)
        
        print("\n=== 游戏即将开始 ===\n")
        time.sleep(2)
        
        self.run_game_loop()
        
    def get_judge_comment(self, event_type: str, **kwargs) -> str:
        """获取AI裁判的评论"""
        if not self.game_state.judge or not self.game_state.judge.ai_controller:
            return None
            
        return self.game_state.judge.ai_controller.comment_on_event(event_type, **kwargs)

    def run_game_loop(self):
        """运行游戏主循环"""
        while len([p for p in self.game_state.players if p.is_alive]) > 2:  # 剩余2名玩家时结束
            self.game_state.current_round += 1
            print(f"\n=== 第{self.game_state.current_round}轮开始 ===\n")
            
            # 简化轮次开始的AI裁判评论
            print(f"AI裁判: 第{self.game_state.current_round}轮游戏开始")
            time.sleep(1)
            
            # 陈述环节
            self.statement_phase()
            
            # 质询环节
            self.interrogation_phase()
            
            # 投票环节
            self.voting_phase()
            
            # 淘汰阶段
            self.elimination_phase()

            # 记录本轮游戏历史
            self.record_round_history()
            
            # 简化轮次结束的AI裁判评论
            if self.elimination_record and len(self.elimination_record) > 0:
                eliminated_player_record = self.elimination_record[-1]
                eliminated_player_name = eliminated_player_record["player"].role_name
                print(f"\nAI裁判: 第{self.game_state.current_round}轮结束，{eliminated_player_name}被淘汰")
            else:
                print(f"\nAI裁判: 第{self.game_state.current_round}轮结束")
            time.sleep(2)

        # 游戏结束
        self.end_game()

    def statement_phase(self):
        """陈述环节"""
        print("\n--- 陈述环节开始 ---")
        print("AI裁判: 陈述环节开始，每位玩家将轮流陈述")
        time.sleep(1)
            
        # 定义发言顺序
        speaking_order = ["豆包", "Kimi", "DeepSeek", "Qwen", "GPT", "Claude", "Gemini", "Grok"]
        
        # 按照指定顺序让玩家发言
        for role_name in speaking_order:
            # 找到对应角色的玩家
            player = next((p for p in self.game_state.players if p.role_name == role_name and p.is_alive), None)
            if player:
                print(f"\n{player.role_name}的陈述：")
                
                # 如果是调试模式，显示原始故事背景
                if os.environ.get("DEBUG_MODE", "0") == "1":
                    print("原始故事背景：")
                    print(player.original_backstory)
                
                # 如果是AI玩家，可以根据游戏进程更新陈述
                if player.is_ai and player.ai_controller:
                    # 获取之前轮次的游戏记录，用于调整陈述
                    previous_rounds = self.game_state.round_history if self.game_state.current_round > 1 else None
                    
                    # 更新陈述内容 - 无论是第一轮还是后续轮次，都尝试生成虚构陈述
                    try:
                        # 收集其他玩家的陈述作为参考
                        other_statements = []
                        if self.game_state.current_round > 1:
                            for other_player in self.game_state.players:
                                if other_player != player and other_player.is_alive and other_player.fake_memory:
                                    other_statements.append(other_player.fake_memory)
                        
                        updated_statement = player.ai_controller.generate_fake_statement_based_on_backstory(
                            player.original_backstory,
                            current_round=self.game_state.current_round,
                            other_statements=other_statements
                        )
                        player.fake_memory = updated_statement
                        player.statement_history.append(updated_statement)
                        print(f"{player.role_name}生成了虚构陈述")
                    except Exception as e:
                        # 如果生成失败，使用预定义故事背景
                        print(f"生成虚构陈述失败：{str(e)}，使用原始背景")
                        if self.game_state.current_round > 1 and previous_rounds:
                            # 如果不是第一轮，尝试更新陈述
                            updated_statement = player.ai_controller.update_statement_with_backstory(
                                player.fake_memory, 
                                previous_rounds
                            )
                            player.fake_memory = updated_statement
                            player.statement_history.append(updated_statement)
                        else:
                            # 第一轮且生成失败，使用原始背景
                            player.statement_history.append(player.fake_memory)
                    
                print(f"陈述内容：{player.fake_memory}")
                time.sleep(2)
        
        print("\nAI裁判: 陈述环节结束")
        time.sleep(1)

    def interrogation_phase(self):
        """质询环节"""
        print("\n--- 质询环节开始 ---")
        print("AI裁判: 质询环节开始，每位玩家将有机会质询其他玩家")
        time.sleep(1)
            
        alive_players = [p for p in self.game_state.players if p.is_alive]
        
        # 记录本轮质询内容
        interrogation_records = []
        
        for questioner in alive_players:
            # 随机选择一个质询目标，确保不是自己
            target = random.choice([p for p in alive_players if p != questioner])
            print(f"\n{questioner.role_name}正在质询{target.role_name}...")
            
            # 使用AI生成质询问题，确保传递完整的target陈述
            if questioner.is_ai and questioner.ai_controller:
                question = questioner.ai_controller.generate_question(
                    questioner.role_name, 
                    target.role_name, 
                    target.fake_memory, 
                    target.trauma  # 使用创伤作为职业描述，增加信息量
                )
            else:
                # 如果不是AI玩家，使用预设问题列表
                questions = [
                    f"你提到的{random.choice(['经历', '动机', '背景'])}是否真实？",
                    "你能详细描述一下你的具体经历吗？",
                    "为什么你会有这样的秘密动机？",
                    "你的陈述中有什么是你没有告诉我们的？"
                ]
                question = random.choice(questions)
            
            # 确保问题不为空，如果API调用失败则使用备选问题
            if not question or len(question.strip()) == 0:
                question = f"你在陈述中提到的{random.choice(['事件', '背景', '动机'])}真的可信吗？"
                
            print(f"{questioner.role_name}: {question}")
            time.sleep(1)
            
            # 如果是AI玩家，使用AI生成回答
            if target.is_ai and target.ai_controller:
                response = target.ai_controller.answer_interrogation(
                    target.role_name, questioner.role_name, question
                )
            else:
                responses = [
                    "我...我说的都是真的...",
                    "这个细节可能有些模糊了，但我确实经历过...",
                    "让我想想，怎么解释更清楚...",
                    "我确定我没有隐瞒任何事情..."
                ]
                response = random.choice(responses)
            
            # 确保回答不为空
            if not response or len(response.strip()) == 0:
                response = "这是个复杂的问题...让我思考一下如何回答。"
                
            print(f"{target.role_name}: {response}")
            time.sleep(1)
            
            # 记录质询内容
            interrogation_record = {
                "questioner": questioner.name,
                "target": target.name,
                "question": question,
                "response": response
            }
            interrogation_records.append(interrogation_record)
            
            # 将质询记录添加到目标玩家的质询历史中
            target.interrogation_history.append(interrogation_record)
            
            # 增加压力值
            target.stress_level += 1
            if target.stress_level >= 3:
                print(f"{target.role_name}表现出明显的紧张症状...")
                time.sleep(1)
            
            time.sleep(1)
        
        # 将本轮质询记录添加到游戏状态中
        self.game_state.round_history.append({"round": self.game_state.current_round, "interrogations": interrogation_records})
        
        print("\nAI裁判: 质询环节结束")
        time.sleep(1)

    def voting_phase(self):
        """投票环节"""
        print("\n--- 投票环节开始 ---")
        
        print("AI裁判: 投票环节开始，每位玩家将依次投票")
        time.sleep(1)
            
        alive_players = [p for p in self.game_state.players if p.is_alive]
        self.voting_results = {p.name: 0 for p in alive_players}
        
        # 记录每个玩家投票给谁的字典及投票理由
        voting_details = {}
        voting_reasons = {}
        voting_records = []
        
        # 收集当前轮次所有玩家的陈述内容和问答记录，用于投票决策
        player_statements = {}
        for player in alive_players:
            player_statements[player.name] = {
                "name": player.name,
                "role_name": player.role_name,
                "trauma": player.trauma,
                "secret_motive": player.secret_motive,
                "statement": player.fake_memory
            }
        
        # 收集当前轮次的问答记录
        current_round_qa = []
        if self.game_state.round_history and len(self.game_state.round_history) > 0:
            # 获取最新一轮的问答记录
            current_round = self.game_state.current_round
            for round_data in self.game_state.round_history:
                if round_data.get("round") == current_round and "interrogations" in round_data:
                    for qa in round_data["interrogations"]:
                        questioner_name = next((p.role_name for p in self.game_state.players if p.name == qa["questioner"]), "未知")
                        target_name = next((p.role_name for p in self.game_state.players if p.name == qa["target"]), "未知")
                        current_round_qa.append({
                            "questioner": questioner_name,
                            "target": target_name,
                            "question": qa["question"],
                            "response": qa["response"]
                        })
        
        for voter in alive_players:
            # 排除自己
            possible_targets = [p for p in alive_players if p != voter]
            
            if voter.is_ai and voter.ai_controller:
                # 如果是AI玩家，使用AI进行投票
                other_player_info = []
                for p in possible_targets:
                    # 为每个候选玩家准备信息
                    player_info = player_statements.get(p.name, {})
                    
                    # 找出与该玩家相关的问答
                    player_qa = []
                    for qa in current_round_qa:
                        if qa["target"] == p.role_name:
                            player_qa.append(f"{qa['questioner']}问: {qa['question']}\n{qa['target']}答: {qa['response']}")
                        # 也添加该玩家作为提问者的记录
                        elif qa["questioner"] == p.role_name:
                            player_qa.append(f"{qa['questioner']}对{qa['target']}提问: {qa['question']}\n{qa['target']}回答: {qa['response']}")
                    
                    # 添加历史陈述记录，如果有的话
                    if hasattr(p, 'statement_history') and p.statement_history:
                        player_info["statement_history"] = p.statement_history[-2:] if len(p.statement_history) > 1 else p.statement_history  # 最多保留最近两次陈述
                    
                    player_info["qa_history"] = player_qa
                    other_player_info.append(player_info)
                
                print(f"DEBUG - {voter.role_name}正在进行投票分析...")
                vote_result = voter.ai_controller.vote(other_player_info)
                
                # 解析AI的投票结果，获取目标和理由
                if isinstance(vote_result, dict) and "target" in vote_result:
                    target_name = vote_result["target"]
                    vote_reason = vote_result.get("reason", "未提供理由")
                    # 确保target_name是有效的玩家名称
                    target = next((p for p in possible_targets if p.name == target_name), None)
                    if target:
                        voting_reasons[voter.name] = vote_reason
                    else:
                        print(f"警告: 投票目标 {target_name} 无效，随机选择一个目标")
                        target = random.choice(possible_targets)
                        voting_reasons[voter.name] = "投票目标无效，随机选择"
                else:
                    # 兼容旧版本返回格式或处理失败情况
                    print(f"警告: {voter.role_name}的投票结果格式无效，随机选择一个目标")
                    target = random.choice(possible_targets)
                    voting_reasons[voter.name] = "投票分析失败，随机选择"
            else:
                target = random.choice(possible_targets)
                voting_reasons[voter.name] = "直觉判断"
            
            # 记录投票详情
            voting_details[voter.name] = target.name
            self.voting_results[target.name] += 1
            
            # 添加到投票记录
            voting_record = {
                "voter": voter.name,
                "target": target.name,
                "reason": voting_reasons[voter.name]
            }
            voting_records.append(voting_record)
            voter.vote_history.append(voting_record)
            
            # 显示投票情况并让AI裁判确认
            print(f"{voter.role_name} 投票给了 {target.role_name}，理由：{voting_reasons[voter.name]}")
            
            # AI裁判对每次投票的确认
            vote_comment = self.get_judge_comment("vote", 
                                               voter=voter.role_name, 
                                               target=target.role_name)
            if vote_comment:
                print(f"AI裁判: {vote_comment}")
                time.sleep(0.5)
        
        # 统计并显示投票结果
        vote_summary = []
        for player_name, votes in self.voting_results.items():
            player = next(p for p in self.game_state.players if p.name == player_name)
            vote_summary.append(f"{player.role_name}: {votes}票")
        
        vote_summary_str = ", ".join(vote_summary)
        print("\n投票统计结果：")
        print(vote_summary_str)
        
        # AI裁判统计票数
        voting_summary_comment = self.get_judge_comment("voting_summary", vote_summary=vote_summary_str)
        if voting_summary_comment:
            print(f"AI裁判: {voting_summary_comment}")
            time.sleep(1)
        
        # 将本轮投票记录添加到游戏状态中
        self.game_state.round_history[-1]["votes"] = voting_records
        
        # 找出最高票数并处理平票情况
        has_clear_winner = False
        revote_count = 0
        max_revotes = 3  # 最多重新投票3次，避免无限循环
        
        while not has_clear_winner and revote_count <= max_revotes:
            max_votes = max(self.voting_results.values())
            most_voted = [p for p, v in self.voting_results.items() if v == max_votes]
            
            if len(most_voted) == 1 or revote_count == max_revotes:
                # 只有一个最高票或已达到最大重投次数，确定被处决者
                has_clear_winner = True
                if len(most_voted) > 1:
                    print(f"\n经过{revote_count}轮重新投票后仍然平票！最终随机选择一名玩家...")
                    self.current_condemned = random.choice(most_voted)
                    
                    # 显示随机选择结果
                    chosen_player = next(p.role_name for p in self.game_state.players if p.name == self.current_condemned)
                    print(f"AI裁判: 随机选择结果：{chosen_player}被淘汰。")
                else:
                    self.current_condemned = most_voted[0]
            else:
                # 出现平票，重新投票
                revote_count += 1
                print(f"\n出现平票！进行第{revote_count}轮重新投票...")
                
                # 显示平票情况
                tied_players_names = [next(p.role_name for p in self.game_state.players if p.name == name) for name in most_voted]
                print(f"AI裁判: 平票玩家: {', '.join(tied_players_names)}")
                time.sleep(1)
                
                # 重置投票结果，只针对平票的玩家
                tied_players = [p for p in most_voted]
                self.voting_results = {p: 0 for p in tied_players}
                
                # 新增：记录重新投票的详情
                revote_details = {}
                
                # 只有存活的玩家可以投票
                alive_players = [p for p in self.game_state.players if p.is_alive]
                
                for voter in alive_players:
                    # 如果是AI玩家，使用AI进行投票
                    if voter.is_ai and voter.ai_controller:
                        # 为平票的玩家准备信息
                        tied_player_info = []
                        for tied_name in tied_players:
                            tied_player = next((p for p in self.game_state.players if p.name == tied_name), None)
                            if tied_player:
                                player_info = {
                                    "name": tied_player.name,
                                    "role_name": tied_player.role_name,
                                    "trauma": tied_player.trauma,
                                    "secret_motive": tied_player.secret_motive,
                                    "statement": tied_player.fake_memory
                                }
                                
                                # 找出与该玩家相关的问答
                                player_qa = []
                                for qa in current_round_qa:
                                    if qa["target"] == tied_player.role_name:
                                        player_qa.append(f"{qa['questioner']}问: {qa['question']}\n{qa['target']}答: {qa['response']}")
                                    # 也添加该玩家作为提问者的记录
                                    elif qa["questioner"] == tied_player.role_name:
                                        player_qa.append(f"{qa['questioner']}对{qa['target']}提问: {qa['question']}\n{qa['target']}回答: {qa['response']}")
                                
                                # 添加历史陈述记录，如果有的话
                                if hasattr(tied_player, 'statement_history') and tied_player.statement_history:
                                    player_info["statement_history"] = tied_player.statement_history[-2:] if len(tied_player.statement_history) > 1 else tied_player.statement_history  # 最多保留最近两次陈述
                                
                                player_info["qa_history"] = player_qa
                                tied_player_info.append(player_info)
                        
                        vote_result = voter.ai_controller.vote(tied_player_info)
                        
                        if isinstance(vote_result, dict) and "target" in vote_result:
                            target_name = vote_result["target"]
                        else:
                            target_name = vote_result.strip()
                            
                        target = next((p for p in tied_players if p == target_name), random.choice(tied_players))
                    else:
                        target = random.choice(tied_players)
                    
                    # 记录重新投票详情
                    revote_details[voter.name] = target
                    self.voting_results[target] += 1
                
                    # 显示重新投票情况并让AI裁判确认
                    voter_role = voter.role_name
                    target_role = next(p.role_name for p in self.game_state.players if p.name == target)
                    print(f"{voter_role} 投票给了 {target_role}")
                    
                    # AI裁判确认重新投票
                    vote_comment = self.get_judge_comment("vote", 
                                                       voter=voter_role, 
                                                       target=target_role)
                    if vote_comment:
                        print(f"AI裁判: {vote_comment}")
                        time.sleep(0.5)
                
                # 统计并显示重新投票结果
                revote_summary = []
                for player_name, votes in self.voting_results.items():
                    player_role = next(p.role_name for p in self.game_state.players if p.name == player_name)
                    revote_summary.append(f"{player_role}: {votes}票")
                
                revote_summary_str = ", ".join(revote_summary)
                print("\n重新投票统计结果：")
                print(revote_summary_str)
                
                # AI裁判统计重新投票结果
                voting_summary_comment = self.get_judge_comment("voting_summary", vote_summary=revote_summary_str)
                if voting_summary_comment:
                    print(f"AI裁判: {voting_summary_comment}")
                    time.sleep(1)
        
        condemned_player = next(p for p in self.game_state.players if p.name == self.current_condemned)
        print(f"\n被处决者：{condemned_player.role_name}")
        print(f"AI裁判: {condemned_player.role_name}获得了最高票数（{self.voting_results[self.current_condemned]}票），将被淘汰。")

    def elimination_phase(self):
        """淘汰阶段"""
        print("\n--- 淘汰阶段 ---")
        
        print("AI裁判: 淘汰阶段开始")
        time.sleep(1)
        
        # 找到被淘汰的玩家
        eliminated_player = next(p for p in self.game_state.players if p.name == self.current_condemned)
        eliminated_player.is_alive = False
        self.game_state.eliminated_players.append(eliminated_player)
        
        # 记录本轮被淘汰的玩家
        self.elimination_record.append({
            "round": self.game_state.current_round,
            "player": eliminated_player
        })
        
        print(f"\n{eliminated_player.role_name}被淘汰，无法逃离地牢...")
        print(f"AI裁判: {eliminated_player.role_name}已被淘汰")
        time.sleep(1)
            
        print("\n幸存者的评论：")
        
        comments = [
            "又少了一个竞争者...",
            "这只是一场生存游戏，没有对错...",
            "希望你在地牢的另一边能找到出路...",
            "我们必须继续前进，才能找到逃离的方法..."
        ]
        
        print(random.choice(comments))
        time.sleep(2)
        
        remaining_players = len([p for p in self.game_state.players if p.is_alive])
        print(f"AI裁判: 淘汰阶段结束，剩余{remaining_players}名玩家")

    def record_round_history(self):
        """记录本轮游戏历史"""
        # 确保本轮历史已经创建
        if not self.game_state.round_history or self.game_state.round_history[-1]["round"] != self.game_state.current_round:
            self.game_state.round_history.append({"round": self.game_state.current_round})
            
        # 添加淘汰记录
        if self.elimination_record and self.elimination_record[-1]["round"] == self.game_state.current_round:
            self.game_state.round_history[-1]["eliminated"] = self.elimination_record[-1]["player"].name

    def end_game(self):
        """游戏结束"""
        winners = [p for p in self.game_state.players if p.is_alive]
        print(f"\n=== 游戏结束 ===\n")
        print(f"恭喜！{winners[0].role_name} 和 {winners[1].role_name} 成功逃离地牢！")
        
        print(f"AI裁判: 游戏结束，{winners[0].role_name} 和 {winners[1].role_name} 是最后的幸存者。")
        time.sleep(1)
        
        # 展示每轮淘汰记录
        print("\n=== 淘汰记录 ===\n")
        if self.elimination_record:
            for record in self.elimination_record:
                print(f"第{record['round']}轮: {record['player'].role_name} 被淘汰")
        else:
            print("本局游戏没有玩家被淘汰")
        
        # 真相揭露
        print("\n=== 真相揭露 ===")
        print("地牢守卫揭露了一个惊人的事实：所有玩家都被告知自己是唯一的'说谎者'...")
        
        print("AI裁判: 真相揭露，所有玩家都被告知自己是唯一的'说谎者'。")
        time.sleep(1)
        
        for winner in winners:
            reaction = f"{winner.role_name}: 原来如此...这一切都是一场心理博弈。我们每个人都在试图掩盖自己的'说谎者'身份..."
            print(reaction)
            time.sleep(1)
        
        print("\n恭喜！你们两位成功逃离了地牢！")
        
        # 游戏复盘环节
        print("\n=== 游戏复盘 ===")
        print("幸存者正在对整场游戏进行复盘分析...\n")
        
        # 准备淘汰记录字符串
        elimination_record_str = ""
        if self.elimination_record:
            for record in self.elimination_record:
                elimination_record_str += f"第{record['round']}轮: {record['player'].role_name} 被淘汰\n"
        else:
            elimination_record_str = "本局游戏没有玩家被淘汰"
        
        # 收集游戏上下文
        game_context = self.collect_game_context()
        print(f"已收集游戏上下文，共{len(game_context)}字符")
        
        # 每位获胜者进行游戏复盘
        for winner in winners:
            if winner.is_ai and winner.ai_controller:
                print(f"\n{winner.role_name}的游戏复盘：")
                review = winner.ai_controller.review_game(
                    name=winner.role_name,
                    trauma=winner.trauma,
                    secret_motive=winner.secret_motive,
                    memory=winner.fake_memory,
                    final_score=100.0,  # 设置一个默认分数
                    elimination_record=elimination_record_str,
                    game_context=game_context
                )
                print(review)
                time.sleep(1)
        
        # 替换AI裁判的游戏总结为简单的结束语
        print("\n=== AI裁判总结 ===\n")
        print(f"AI裁判: 游戏结束，{winners[0].role_name} 和 {winners[1].role_name} 是最后的幸存者。感谢所有玩家的参与！")
    
    def collect_game_context(self) -> str:
        """收集整场游戏的上下文信息，用于复盘"""
        context = []
        
        # 添加玩家信息
        context.append("【玩家信息】")
        for player in self.game_state.players:
            status = "幸存" if player.is_alive else "被淘汰"
            context.append(f"{player.role_name}({status}): {player.trauma}")
        
        # 添加每轮游戏记录
        context.append("\n【游戏过程】")
        for round_data in self.game_state.round_history:
            round_num = round_data.get("round", "未知")
            context.append(f"\n第{round_num}轮:")
            
            # 陈述内容
            context.append("- 陈述环节:")
            for player in self.game_state.players:
                if len(player.statement_history) >= round_num:
                    statement = player.statement_history[round_num-1]
                    context.append(f"  {player.role_name}: {statement[:150]}..." if len(statement) > 150 else f"  {player.role_name}: {statement}")
            
            # 质询环节
            if "interrogations" in round_data:
                context.append("- 质询环节:")
                for qa in round_data["interrogations"]:
                    questioner = next((p.role_name for p in self.game_state.players if p.name == qa["questioner"]), "未知")
                    target = next((p.role_name for p in self.game_state.players if p.name == qa["target"]), "未知")
                    context.append(f"  {questioner} 质询 {target}: {qa['question']}")
                    context.append(f"  {target} 回答: {qa['response']}")
            
            # 投票环节
            if "votes" in round_data:
                context.append("- 投票环节:")
                for vote in round_data["votes"]:
                    voter = next((p.role_name for p in self.game_state.players if p.name == vote["voter"]), "未知")
                    target = next((p.role_name for p in self.game_state.players if p.name == vote["target"]), "未知")
                    reason = vote.get("reason", "未提供理由")
                    context.append(f"  {voter} 投票给 {target}, 理由: {reason}")
            
            # 淘汰结果
            if "eliminated" in round_data:
                eliminated = round_data["eliminated"]
                eliminated_player = next((p.role_name for p in self.game_state.players if p.name == eliminated), "未知")
                context.append(f"- 淘汰结果: {eliminated_player} 被淘汰")
        
        return "\n".join(context)

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="AI地牢生存游戏")
    parser.add_argument("--debug", action="store_true", help="启用调试模式，显示原始故事背景")
    args = parser.parse_args()
    
    # 设置调试模式环境变量
    if args.debug:
        os.environ["DEBUG_MODE"] = "1"
        print("调试模式已启用，将显示原始故事背景")
    
    game = GameManager()
    game.start_game()

if __name__ == "__main__":
    from output_handler import redirect_output
    
    # 使用输出重定向上下文管理器，启用简化模式
    with redirect_output(simplified=True):
        main()