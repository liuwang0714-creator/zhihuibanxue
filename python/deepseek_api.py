# coding: utf-8
"""DeepSeek API 调用模块 —— 智学伴行 AI 引擎"""
import requests
import json

# ==================== DeepSeek 配置 ====================
DEEPSEEK_API_KEY = ""
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"  # DeepSeek-V3 (latest)


def call_deepseek_ai(query, system_prompt=None, temperature=0.7, max_tokens=4096):
    """
    调用 DeepSeek API，返回 AI 回答内容
    
    Args:
        query (str): 用户问题
        system_prompt (str): 系统提示词（角色设定）
        temperature (float): 温度参数（0-2，越高越随机）
        max_tokens (int): 最大输出 token 数
    
    Returns:
        str: AI 的回答内容
    """
    url = f"{DEEPSEEK_BASE_URL}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": query})
    
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        raise Exception("AI 响应超时，请稍后重试")
    except requests.exceptions.RequestException as e:
        raise Exception(f"AI 调用失败: {str(e)}")
    except (KeyError, IndexError) as e:
        raise Exception(f"AI 响应格式异常: {str(e)}")


def call_deepseek_stream(query, system_prompt=None, temperature=0.7, max_tokens=4096):
    """
    流式调用 DeepSeek API（用于长文本生成，如写作）
    返回生成器，逐个产出文本片段
    """
    url = f"{DEEPSEEK_BASE_URL}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": query})
    
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=120, stream=True)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data_str = line[6:]
                    if data_str == '[DONE]':
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
    except Exception as e:
        raise Exception(f"AI 流式调用失败: {str(e)}")


def call_deepseek_chat(messages, temperature=0.7, max_tokens=4096):
    """
    多轮对话调用 DeepSeek API
    
    Args:
        messages (list): [{"role": "system/user/assistant", "content": "..."}]
        temperature (float): 温度参数
        max_tokens (int): 最大输出 token 数
    
    Returns:
        str: AI 的回答内容
    """
    url = f"{DEEPSEEK_BASE_URL}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        raise Exception(f"AI 多轮对话失败: {str(e)}")


# ==================== 专门的 AI 功能函数 ====================

def ai_tutor_answer(course_name, question, chat_history=None):
    """AI智能答疑"""
    system = f"""你是「智学伴行」的AI学习助教，正在辅导《{course_name}》课程。
你的回答应该：
1. 准确、专业、深入浅出
2. 分点清晰，便于理解
3. 如果有多种解法或理解角度，都要列出
4. 最后给出一个拓展思考题，引导深入学习
5. 语言亲切但不失专业

请用中文回答。"""
    
    messages = [{"role": "system", "content": system}]
    if chat_history:
        messages.extend(chat_history)
    messages.append({"role": "user", "content": question})
    
    return call_deepseek_chat(messages, temperature=0.7, max_tokens=4096)


def ai_generate_learning_path(course_name):
    """AI生成个性化学习路径"""
    prompt = f"""请为课程《{course_name}》生成5-7条系统化的学习路径步骤。
要求：
1. 从基础到进阶，逻辑递进
2. 每一步描述控制在20字以内，简洁明了
3. 按 "1. 步骤描述" 格式输出
4. 覆盖核心知识点和关键技能
5. 只输出步骤，不要添加额外说明文字

示例格式：
1. 掌握Python基础语法
2. 学习函数与模块编程
3. 理解面向对象编程
4. 掌握文件操作与异常处理
5. 学习常用标准库
6. 完成小型项目实战"""
    
    return call_deepseek_ai(prompt, temperature=0.5, max_tokens=2000)


def ai_recommend_materials(course_name, topic=""):
    """智能资料推荐"""
    topic_str = f"关于「{topic}」" if topic else ""
    prompt = f"""你是学习资料推荐专家。针对课程《{course_name}》{topic_str}，请推荐5-8个高质量学习资源。
要求：
1. 包含不同类型：书籍、在线课程、视频、文章、练习平台等
2. 每个资源包含：名称、类型、推荐理由（1-2句）
3. 按推荐优先级排列
4. 格式：序号. 【类型】名称 —— 推荐理由

只输出推荐列表即可。"""
    
    return call_deepseek_ai(prompt, temperature=0.6, max_tokens=3000)


def ai_write_paper(topic, paper_type="论文", requirements=""):
    """AI论文写作助手"""
    req_str = f"\n额外要求：{requirements}" if requirements else ""
    prompt = f"""请帮我撰写一篇{paper_type}，主题为「{topic}」。{req_str}

请按以下结构输出：
1. **标题**：一个吸引人且准确反映内容的标题
2. **摘要**：200字左右的核心内容概述
3. **大纲**：列出3-5个主要章节及其子要点
4. **引言**：开篇段落（300-500字）
5. **正文框架**：每个章节的核心论点
6. **结论**：总结要点与展望
7. **参考文献建议**：推荐3-5篇相关文献

注意：
- 内容学术规范，逻辑清晰
- 中文为主，专业术语可保留英文
- 数据与案例需要时给出合理示例"""
    
    return call_deepseek_ai(prompt, temperature=0.7, max_tokens=8000)


def ai_generate_report(topic, report_type="实验报告", requirements=""):
    """AI报告/PPT生成"""
    req_str = f"\n额外要求：{requirements}" if requirements else ""
    prompt = f"""请帮我生成一份{report_type}，主题为「{topic}」。{req_str}

请按以下结构输出：
1. **报告标题**
2. **背景与目的**（100-200字）
3. **方法与过程**（分步骤说明）
4. **结果与分析**（含数据呈现建议）
5. **讨论**（2-3个讨论点）
6. **结论**
7. **附录/参考资料**

注意：
- 实验报告要有"实验目的-原理-步骤-结果-讨论"完整结构
- 调研报告要有"背景-方法-发现-分析-建议"完整结构
- 格式规范，适合直接使用"""
    
    return call_deepseek_ai(prompt, temperature=0.7, max_tokens=6000)


def ai_error_book_analysis(errors_text, subject=""):
    """错题分析与知识图谱"""
    subject_str = f"（学科：{subject}）" if subject else ""
    prompt = f"""你是学习分析专家。请分析以下错题{subject_str}：

{errors_text}

请输出：
1. **错题归类**：按知识点分类，标注错误类型（概念不清/计算失误/思路错误/粗心等）
2. **薄弱点诊断**：分析暴露出的薄弱知识点
3. **改进建议**：针对每个薄弱点的具体改进方案
4. **推荐练习**：每个薄弱点推荐1-2道针对性练习题（只需描述题目大意）
5. **知识图谱提示**：用关键词标记涉及的关联知识点（如：函数→导数→极限→连续性）

格式清晰，有实际指导价值。"""
    
    return call_deepseek_ai(prompt, temperature=0.5, max_tokens=5000)


def ai_study_supervisor(study_data):
    """学习监督与激励分析"""
    prompt = f"""你是学习激励教练。请根据以下学习数据，生成一份学习监督与激励报告：

学习数据：
{study_data}

请输出：
1. **学习概况**：总体评价（积极性/完成度/趋势）
2. **亮点表扬**：指出做得好的方面，给予具体表扬
3. **改进建议**：需要提升的方向和具体方法
4. **本周目标**：设定3个具体可达成的学习目标
5. **激励语**：一段温暖的鼓励话语（50-100字）

语气要温暖、鼓励、像朋友一样，但不失专业性。"""
    
    return call_deepseek_ai(prompt, temperature=0.8, max_tokens=3000)


# ==================== 测试 ====================
if __name__ == '__main__':
    # 简单测试
    result = call_deepseek_ai("用一句话介绍你自己")
    print("DeepSeek 测试结果：")
    print(result)
