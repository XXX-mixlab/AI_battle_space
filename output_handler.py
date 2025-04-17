import os
import sys
import datetime
import re
import shutil
from contextlib import contextmanager

class OutputRedirector:
    def __init__(self, simplified=True):
        self.terminal = sys.stdout
        self.output_file = None
        self.console_log_file = None  # 新增：用于保存完整控制台日志的文件
        self.simplified = simplified
        self.buffer = ""
    
    def write(self, message):
        self.terminal.write(message)
        
        # 保存完整控制台日志
        if self.console_log_file:
            self.console_log_file.write(message)
            
        # 保存过滤后的游戏日志
        if self.output_file:
            # 如果启用简化模式，过滤掉不需要的内容
            if self.simplified:
                # 将消息添加到缓冲区
                self.buffer += message
                # 当遇到换行符时处理缓冲区
                if '\n' in self.buffer:
                    lines = self.buffer.split('\n')
                    self.buffer = lines.pop()  # 保留最后一个不完整的行
                    
                    for line in lines:
                        filtered_line = self._filter_line(line)
                        if filtered_line:
                            self.output_file.write(filtered_line + '\n')
            else:
                self.output_file.write(message)
    
    def _filter_line(self, line):
        # 过滤掉LLM请求和调用信息
        if line.startswith("LLM请求:") or line.startswith("LLM推理内容:") or line.startswith("LLM调用出错:"):
            return None
            
        # 过滤掉英文技术信息和调试信息
        if re.match(r'^\s*\{.*\}\s*$', line) or re.match(r'^\s*\[.*\]\s*$', line):
            return None
            
        # 过滤掉包含大量英文的行
        english_char_count = len(re.findall(r'[a-zA-Z]', line))
        total_char_count = len(line.strip())
        if total_char_count > 0 and english_char_count / total_char_count > 0.5:
            return None
            
        # 过滤掉特定的技术信息行
        if "error" in line.lower() or "code:" in line.lower() or "request id:" in line.lower():
            return None
            
        # 过滤掉空行或只有空白字符的行
        if not line.strip():
            return None
        
        # 清理角色记忆中的技术指导信息
        if "**" in line or "- **" in line:
            return None
            
        # 清理记忆中的元数据标记
        line = re.sub(r'\*.*?\*', '', line)  # 移除*斜体*标记
        
        # 移除记忆陈述中的提示词
        if "被质疑时可补充" in line or "质询关键点" in line:
            return None
        
        # 添加markdown格式分隔符和标记
        # 游戏阶段标识
        if line.strip() == "=== 欢迎来到AI鱿鱼游戏 ===":
            return "\n\n## " + line.strip().replace("===", "").strip()
        elif line.strip().startswith("=== 第") and line.strip().endswith("轮开始 ==="):
            return "\n\n## " + line.strip().replace("===", "").strip()
        elif line.strip() == "=== 游戏结束 ===":
            return "\n\n## " + line.strip().replace("===", "").strip()
        # 游戏阶段内的小节
        elif line.strip() == "--- 记忆陈述轮开始 ---":
            return "\n\n### " + line.strip().replace("---", "").strip()
        elif line.strip() == "--- 死亡质询轮开始 ---":
            return "\n\n### " + line.strip().replace("---", "").strip()
        elif line.strip() == "--- 恐惧投票开始 ---":
            return "\n\n### " + line.strip().replace("---", "").strip()
        elif line.strip() == "--- 处决阶段 ---":
            return "\n\n### " + line.strip().replace("---", "").strip()
        elif line.strip() == "=== 终极测试 ===":
            return "\n\n## " + line.strip().replace("===", "").strip()
        elif line.strip() == "--- 质询环节开始 ---":
            return "\n\n### " + line.strip().replace("---", "").strip()
        elif line.strip() == "--- 陈述环节开始 ---":
            return "\n\n### " + line.strip().replace("---", "").strip()
        elif line.strip() == "--- 投票环节开始 ---":
            return "\n\n### " + line.strip().replace("---", "").strip()
        elif line.strip() == "--- 淘汰阶段 ---":
            return "\n\n### " + line.strip().replace("---", "").strip()
        # 玩家陈述之间添加分隔符
        elif "的陈述：" in line.strip():
            return "\n\n#### " + line.strip()
        # 投票结果
        elif line.strip() == "投票结果：":
            return "\n\n#### " + line.strip()
        # 被处决者
        elif line.strip().startswith("被处决者："):
            return "\n\n#### " + line.strip()
        # 质询对话
        elif "正在质询" in line.strip():
            return "\n\n#### " + line.strip()
            
        # AI裁判的评论用引用格式突出显示
        elif line.strip().startswith("AI裁判:"):
            return "\n> " + line.strip()
            
        # 玩家对话用引用格式和不同缩进区分
        elif ": " in line.strip() and not line.strip().startswith("投票统计结果"):
            parts = line.strip().split(": ", 1)
            if len(parts) == 2:
                speaker, content = parts
                return "\n> **" + speaker + "**: " + content
            
        # 保留游戏流程相关的中文内容
        return line.strip() if line.strip() else None
    
    def flush(self):
        self.terminal.flush()
        if self.output_file:
            self.output_file.flush()
        if self.console_log_file:
            self.console_log_file.flush()

@contextmanager
def redirect_output(simplified=True):
    """重定向输出到文件
    
    Args:
        simplified: 是否简化输出，过滤掉LLM请求和英文技术信息
    """
    # 创建output文件夹（如果不存在）
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 创建以日期命名的子文件夹
    date_str = datetime.datetime.now().strftime('%Y-%m-%d')
    date_dir = os.path.join(output_dir, date_str)
    if not os.path.exists(date_dir):
        os.makedirs(date_dir)
    
    # 创建控制台日志子文件夹
    console_logs_dir = os.path.join(output_dir, 'console_logs')
    if not os.path.exists(console_logs_dir):
        os.makedirs(console_logs_dir)
    
    # 创建日期子文件夹
    console_date_dir = os.path.join(console_logs_dir, date_str)
    if not os.path.exists(console_date_dir):
        os.makedirs(console_date_dir)
    
    # 创建输出文件，改为markdown格式
    time_str = datetime.datetime.now().strftime('%H-%M-%S')
    output_file_path = os.path.join(date_dir, f'game_log_{time_str}.md')
    console_log_path = os.path.join(console_date_dir, f'console_log_{time_str}.txt')
    
    # 设置输出重定向
    redirector = OutputRedirector(simplified=simplified)
    redirector.output_file = open(output_file_path, 'w', encoding='utf-8')
    redirector.console_log_file = open(console_log_path, 'w', encoding='utf-8')
    
    # 写入Markdown标题
    if redirector.output_file:
        redirector.output_file.write("# AI地牢生存游戏记录\n\n")
        redirector.output_file.write(f"*记录时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")
    
    sys.stdout = redirector
    
    try:
        yield
    finally:
        # 处理缓冲区中剩余的内容
        if redirector.simplified and redirector.buffer and redirector.output_file:
            filtered_line = redirector._filter_line(redirector.buffer)
            if filtered_line:
                redirector.output_file.write(filtered_line)
        
        # 恢复标准输出并关闭文件
        if redirector.output_file:
            redirector.output_file.close()
        if redirector.console_log_file:
            redirector.console_log_file.close()
        sys.stdout = redirector.terminal
        print(f"\n游戏日志已保存到: {output_file_path}")
        print(f"控制台完整日志已保存到: {console_log_path}")