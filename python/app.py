# coding: utf-8
"""
智学伴行 —— AI大学生全能学习助手 后端API
Flask + MySQL + DeepSeek V4 Pro
"""
from flask import Flask, request, jsonify, g
from flask_cors import CORS
import pymysql
from deepseek_api import (
    call_deepseek_ai, call_deepseek_chat,
    ai_tutor_answer, ai_generate_learning_path,
    ai_recommend_materials, ai_write_paper,
    ai_generate_report, ai_error_book_analysis,
    ai_study_supervisor
)

app = Flask(__name__)

# CORS配置
CORS(app, resources=r'/*', supports_credentials=True)

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'ai_learn',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}


def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(**DB_CONFIG)
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


# ==================== 登录验证装饰器 ====================
def login_required(f):
    def wrapper(*args, **kwargs):
        user_email = request.headers.get('X-User-Email')
        if not user_email:
            return jsonify({"status": "fail", "message": "请先登录"}), 401
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
        user = cursor.fetchone()
        cursor.close()
        if not user:
            return jsonify({"status": "fail", "message": "用户不存在"}), 401
        g.user_id = user['id']
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


# ==================== 1. 用户相关 ====================
@app.route("/api/register", methods=['POST'])
def register():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    if not email or not password:
        return jsonify({"status": "fail", "message": "邮箱和密码不能为空"}), 400
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        cursor.close()
        return jsonify({"status": "fail", "message": "该邮箱已注册"}), 400
    try:
        cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, password))
        db.commit()
        cursor.close()
        return jsonify({"status": "success", "message": "注册成功"})
    except Exception as e:
        db.rollback()
        cursor.close()
        return jsonify({"status": "fail", "message": str(e)}), 500


@app.route("/api/login", methods=['POST'])
def login():
    data = request.json
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    if not email or not password:
        return jsonify({"status": "fail", "message": "邮箱和密码不能为空"}), 400
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE email = %s AND password = %s", (email, password))
    user = cursor.fetchone()
    cursor.close()
    if user:
        return jsonify({"status": "success", "message": "登录成功", "email": email})
    return jsonify({"status": "fail", "message": "邮箱或密码错误"}), 401


@app.route("/api/check_login", methods=['GET'])
def check_login():
    user_email = request.headers.get('X-User-Email')
    if not user_email:
        return jsonify({"status": "fail", "message": "未登录"}), 401
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id FROM users WHERE email = %s", (user_email,))
    user = cursor.fetchone()
    cursor.close()
    return jsonify({"status": "success" if user else "fail"})


# ==================== 2. 课程管理 ====================
@app.route("/api/add_course", methods=['POST'])
@login_required
def add_course():
    data = request.json
    course_name = data.get('course_name', '').strip()
    if not course_name:
        return jsonify({"status": "fail", "message": "课程名称不能为空"}), 400
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("INSERT INTO courses (user_id, course_name) VALUES (%s, %s)", (g.user_id, course_name))
        course_id = cursor.lastrowid
        db.commit()

        # AI生成学习路径
        try:
            path_text = ai_generate_learning_path(course_name)
            steps = parse_learning_path(path_text)
            for idx, step_desc in enumerate(steps, 1):
                cursor.execute(
                    "INSERT INTO learning_paths (course_id, step_order, step_description) VALUES (%s, %s, %s)",
                    (course_id, idx, step_desc)
                )
            db.commit()
        except Exception as e:
            print(f"AI学习路径生成失败: {e}")

        cursor.close()
        return jsonify({"status": "success", "message": f"课程《{course_name}》创建成功", "course_id": course_id})
    except Exception as e:
        db.rollback()
        cursor.close()
        return jsonify({"status": "fail", "message": str(e)}), 500


@app.route("/api/get_courses", methods=['GET'])
@login_required
def get_courses():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, course_name, created_at FROM courses WHERE user_id = %s ORDER BY created_at DESC", (g.user_id,))
    courses = cursor.fetchall()
    cursor.close()
    return jsonify(courses)


@app.route("/api/delete_course", methods=['POST'])
@login_required
def delete_course():
    data = request.json
    course_id = data.get('course_id')
    if not course_id:
        return jsonify({"status": "fail", "message": "课程ID不能为空"}), 400
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM courses WHERE id = %s AND user_id = %s", (course_id, g.user_id))
        db.commit()
        cursor.close()
        return jsonify({"status": "success", "message": "课程已删除"})
    except Exception as e:
        db.rollback()
        cursor.close()
        return jsonify({"status": "fail", "message": str(e)}), 500


@app.route("/api/get_course_steps", methods=['GET'])
@login_required
def get_course_steps():
    course_id = request.args.get('course_id')
    if not course_id:
        return jsonify({"status": "fail", "message": "课程ID不能为空"}), 400
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, step_order, step_description, completed FROM learning_paths WHERE course_id = %s ORDER BY step_order",
        (course_id,))
    steps = cursor.fetchall()
    cursor.close()
    return jsonify({"status": "success", "steps": steps})


@app.route("/api/set_completed", methods=['POST'])
@login_required
def set_completed():
    data = request.json
    step_id = data.get('step_id')
    completed = 1 if data.get('completed') else 0
    if not step_id:
        return jsonify({"status": "fail", "message": "步骤ID不能为空"}), 400
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("UPDATE learning_paths SET completed = %s WHERE id = %s", (completed, step_id))
        db.commit()
        cursor.close()

        # 记录学习数据
        if completed:
            cursor2 = db.cursor()
            cursor2.execute(
                "SELECT course_id FROM learning_paths WHERE id = %s", (step_id,))
            row = cursor2.fetchone()
            cursor2.close()
            if row:
                from datetime import date
                cursor3 = db.cursor()
                cursor3.execute(
                    "INSERT INTO study_records (user_id, course_id, study_date, study_minutes, tasks_completed) VALUES (%s,%s,%s,30,1) ON DUPLICATE KEY UPDATE study_minutes=study_minutes+30, tasks_completed=tasks_completed+1",
                    (g.user_id, row['course_id'], date.today())
                )
                db.commit()
                cursor3.close()

        return jsonify({"status": "success"})
    except Exception as e:
        db.rollback()
        cursor.close()
        return jsonify({"status": "fail", "message": str(e)}), 500


# ==================== 3. AI智能答疑（多轮对话支持） ====================
@app.route("/api/ai_tutor", methods=['POST'])
@login_required
def ai_tutor():
    """AI智能答疑 —— 支持多轮对话"""
    data = request.json
    question = data.get('question', '').strip()
    course_id = data.get('course_id')

    if not question:
        return jsonify({"status": "fail", "message": "请输入问题"}), 400

    db = get_db()
    cursor = db.cursor()

    # 获取课程名
    course_name = "通用答疑"
    if course_id:
        cursor.execute("SELECT course_name FROM courses WHERE id = %s AND user_id = %s", (course_id, g.user_id))
        row = cursor.fetchone()
        if row:
            course_name = row['course_name']

    # 获取最近10轮对话历史
    cursor.execute(
        "SELECT role, content FROM ai_conversations WHERE user_id = %s AND course_id = %s ORDER BY id DESC LIMIT 20",
        (g.user_id, course_id or -1))
    history_raw = list(cursor.fetchall())  # 转成列表
    history_raw.reverse()
    chat_history = [{"role": r['role'], "content": r['content']} for r in history_raw]

    # 保存用户问题
    cursor.execute(
        "INSERT INTO ai_conversations (user_id, course_id, role, content) VALUES (%s,%s,'user',%s)",
        (g.user_id, course_id, question))
    db.commit()

    # 调用AI
    try:
        answer = ai_tutor_answer(course_name, question, chat_history)
    except Exception as e:
        cursor.close()
        return jsonify({"status": "fail", "message": f"AI调用失败: {str(e)}"}), 500

    # 保存AI回答
    cursor.execute(
        "INSERT INTO ai_conversations (user_id, course_id, role, content) VALUES (%s,%s,'assistant',%s)",
        (g.user_id, course_id, answer))
    db.commit()
    cursor.close()

    return jsonify({"status": "success", "answer": answer, "course_name": course_name})


@app.route("/api/ai_clear_history", methods=['POST'])
@login_required
def ai_clear_history():
    """清除对话历史"""
    data = request.json
    course_id = data.get('course_id')
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM ai_conversations WHERE user_id = %s AND course_id = %s",
                   (g.user_id, course_id or -1))
    db.commit()
    cursor.close()
    return jsonify({"status": "success", "message": "对话历史已清除"})


# ==================== 4. 个性化学习规划 ====================
@app.route("/api/ai_learning_plan", methods=['POST'])
@login_required
def ai_learning_plan():
    """重新生成/优化学习路径"""
    data = request.json
    course_id = data.get('course_id')
    if not course_id:
        return jsonify({"status": "fail", "message": "请选择课程"}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT course_name FROM courses WHERE id = %s AND user_id = %s", (course_id, g.user_id))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        return jsonify({"status": "fail", "message": "课程不存在"}), 404

    try:
        path_text = ai_generate_learning_path(row['course_name'])
        steps = parse_learning_path(path_text)

        # 清除旧路径
        cursor.execute("DELETE FROM learning_paths WHERE course_id = %s", (course_id,))
        for idx, step_desc in enumerate(steps, 1):
            cursor.execute(
                "INSERT INTO learning_paths (course_id, step_order, step_description) VALUES (%s,%s,%s)",
                (course_id, idx, step_desc))
        db.commit()
        cursor.close()
        return jsonify({"status": "success", "message": "学习路径已重新生成", "steps": steps})
    except Exception as e:
        db.rollback()
        cursor.close()
        return jsonify({"status": "fail", "message": str(e)}), 500


# ==================== 5. 智能资料推荐 ====================
@app.route("/api/ai_materials", methods=['POST'])
@login_required
def ai_materials():
    """智能资料推荐"""
    data = request.json
    course_name = data.get('course_name', '').strip()
    topic = data.get('topic', '').strip()
    course_id = data.get('course_id')

    if not course_name and course_id:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT course_name FROM courses WHERE id = %s AND user_id = %s", (course_id, g.user_id))
        row = cursor.fetchone()
        cursor.close()
        if row:
            course_name = row['course_name']

    if not course_name:
        return jsonify({"status": "fail", "message": "请输入课程名称"}), 400

    try:
        result = ai_recommend_materials(course_name, topic)
    except Exception as e:
        return jsonify({"status": "fail", "message": str(e)}), 500

    # 保存到资料库
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO materials (user_id, course_id, topic, content, material_type) VALUES (%s,%s,%s,%s,'recommend')",
        (g.user_id, course_id, topic or course_name, result))
    db.commit()
    cursor.close()

    return jsonify({"status": "success", "materials": result, "course_name": course_name})


@app.route("/api/get_materials", methods=['GET'])
@login_required
def get_materials():
    """获取历史资料推荐"""
    course_id = request.args.get('course_id')
    db = get_db()
    cursor = db.cursor()
    if course_id:
        cursor.execute(
            "SELECT * FROM materials WHERE user_id = %s AND course_id = %s ORDER BY created_at DESC LIMIT 20",
            (g.user_id, course_id))
    else:
        cursor.execute("SELECT * FROM materials WHERE user_id = %s ORDER BY created_at DESC LIMIT 20", (g.user_id,))
    rows = cursor.fetchall()
    cursor.close()
    return jsonify(rows)


# ==================== 6. AI论文写作助手 ====================
@app.route("/api/ai_write_paper", methods=['POST'])
@login_required
def write_paper():
    """AI论文写作"""
    data = request.json
    topic = data.get('topic', '').strip()
    paper_type = data.get('paper_type', '论文').strip()
    requirements = data.get('requirements', '').strip()
    if not topic:
        return jsonify({"status": "fail", "message": "请输入论文主题"}), 400

    try:
        result = ai_write_paper(topic, paper_type, requirements)
    except Exception as e:
        return jsonify({"status": "fail", "message": str(e)}), 500

    # 保存记录
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO writings (user_id, topic, writing_type, requirements, content) VALUES (%s,%s,%s,%s,%s)",
        (g.user_id, topic, 'paper' if paper_type == '论文' else 'essay', requirements, result[:5000]))
    db.commit()
    cursor.close()

    return jsonify({"status": "success", "content": result, "topic": topic})


# ==================== 7. AI报告/文档生成 ====================
@app.route("/api/ai_generate_report", methods=['POST'])
@login_required
def generate_report():
    """AI报告生成（实验报告/调研报告/PPT大纲）"""
    data = request.json
    topic = data.get('topic', '').strip()
    report_type = data.get('report_type', '实验报告').strip()
    requirements = data.get('requirements', '').strip()
    if not topic:
        return jsonify({"status": "fail", "message": "请输入报告主题"}), 400

    try:
        result = ai_generate_report(topic, report_type, requirements)
    except Exception as e:
        return jsonify({"status": "fail", "message": str(e)}), 500

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO writings (user_id, topic, writing_type, requirements, content) VALUES (%s,%s,%s,%s,%s)",
        (g.user_id, topic, 'report', requirements, result[:5000]))
    db.commit()
    cursor.close()

    return jsonify({"status": "success", "content": result, "topic": topic})


@app.route("/api/get_writings", methods=['GET'])
@login_required
def get_writings():
    """获取写作历史"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, topic, writing_type, requirements, created_at FROM writings WHERE user_id = %s ORDER BY created_at DESC LIMIT 20",
        (g.user_id,))
    rows = cursor.fetchall()
    cursor.close()
    return jsonify(rows)


@app.route("/api/get_writing_detail", methods=['GET'])
@login_required
def get_writing_detail():
    """获取写作详情"""
    writing_id = request.args.get('id')
    if not writing_id:
        return jsonify({"status": "fail", "message": "缺少ID"}), 400
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM writings WHERE id = %s AND user_id = %s", (writing_id, g.user_id))
    row = cursor.fetchone()
    cursor.close()
    if row:
        return jsonify({"status": "success", "writing": row})
    return jsonify({"status": "fail", "message": "记录不存在"}), 404


# ==================== 8. 错题本与知识图谱 ====================
@app.route("/api/ai_error_analysis", methods=['POST'])
@login_required
def error_analysis():
    """提交错题并获得AI分析"""
    data = request.json
    error_content = data.get('error_content', '').strip()
    subject = data.get('subject', '').strip()
    course_id = data.get('course_id')
    if not error_content:
        return jsonify({"status": "fail", "message": "请输入错题内容"}), 400

    try:
        analysis = ai_error_book_analysis(error_content, subject)
    except Exception as e:
        return jsonify({"status": "fail", "message": str(e)}), 500

    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO error_books (user_id, course_id, subject, error_content, ai_analysis) VALUES (%s,%s,%s,%s,%s)",
        (g.user_id, course_id, subject, error_content, analysis))
    error_id = cursor.lastrowid
    db.commit()
    cursor.close()

    return jsonify({"status": "success", "analysis": analysis, "error_id": error_id})


@app.route("/api/get_error_books", methods=['GET'])
@login_required
def get_error_books():
    """获取错题本列表"""
    course_id = request.args.get('course_id')
    db = get_db()
    cursor = db.cursor()
    if course_id:
        cursor.execute(
            "SELECT * FROM error_books WHERE user_id = %s AND course_id = %s ORDER BY created_at DESC",
            (g.user_id, course_id))
    else:
        cursor.execute("SELECT * FROM error_books WHERE user_id = %s ORDER BY created_at DESC", (g.user_id,))
    rows = cursor.fetchall()
    cursor.close()
    return jsonify(rows)


@app.route("/api/delete_error", methods=['POST'])
@login_required
def delete_error():
    """删除错题"""
    data = request.json
    error_id = data.get('error_id')
    if not error_id:
        return jsonify({"status": "fail", "message": "错题ID不能为空"}), 400
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM error_books WHERE id = %s AND user_id = %s", (error_id, g.user_id))
    db.commit()
    cursor.close()
    return jsonify({"status": "success", "message": "已删除"})


@app.route("/api/toggle_error_resolved", methods=['POST'])
@login_required
def toggle_error_resolved():
    """标记错题为已解决"""
    data = request.json
    error_id = data.get('error_id')
    resolved = data.get('resolved', True)
    if not error_id:
        return jsonify({"status": "fail", "message": "错题ID不能为空"}), 400
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE error_books SET resolved = %s WHERE id = %s AND user_id = %s",
                   (1 if resolved else 0, error_id, g.user_id))
    db.commit()
    cursor.close()
    return jsonify({"status": "success"})


# ==================== 9. 学习监督与激励 ====================
@app.route("/api/ai_study_report", methods=['POST'])
@login_required
def study_report():
    """生成学习监督与激励报告"""
    data = request.json
    course_id = data.get('course_id')

    db = get_db()
    cursor = db.cursor()

    # 收集学习数据
    study_data_parts = []

    # 学习记录
    if course_id:
        cursor.execute(
            "SELECT study_date, study_minutes, tasks_completed FROM study_records WHERE user_id = %s AND course_id = %s ORDER BY study_date DESC LIMIT 14",
            (g.user_id, course_id))
    else:
        cursor.execute(
            "SELECT study_date, study_minutes, tasks_completed FROM study_records WHERE user_id = %s ORDER BY study_date DESC LIMIT 14",
            (g.user_id,))
    study_rows = cursor.fetchall()
    if study_rows:
        study_data_parts.append("【近期学习记录】")
        for r in study_rows:
            study_data_parts.append(
                f"日期{r['study_date']}: 学习{r['study_minutes']}分钟, 完成{r['tasks_completed']}个任务")

    # 课程完成情况
    cursor.execute(
        "SELECT c.course_name, COUNT(lp.id) as total, SUM(lp.completed) as done FROM courses c LEFT JOIN learning_paths lp ON c.id=lp.course_id WHERE c.user_id=%s GROUP BY c.id",
        (g.user_id,))
    course_stats = cursor.fetchall()
    if course_stats:
        study_data_parts.append("\n【课程进度】")
        for cs in course_stats:
            total = cs['total'] or 0
            done = cs['done'] or 0
            pct = int(done / total * 100) if total > 0 else 0
            study_data_parts.append(f"{cs['course_name']}: {done}/{total} 完成 ({pct}%)")

    # 错题统计
    cursor.execute("SELECT COUNT(*) as cnt FROM error_books WHERE user_id = %s", (g.user_id,))
    err_cnt = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM error_books WHERE user_id = %s AND resolved=1", (g.user_id,))
    err_resolved = cursor.fetchone()['cnt']
    study_data_parts.append(f"\n【错题统计】共{err_cnt}道错题，已解决{err_resolved}道")

    cursor.close()

    study_data = "\n".join(study_data_parts)
    if not study_data.strip():
        return jsonify({"status": "fail", "message": "暂无学习数据，先开始学习吧！"}), 400

    try:
        report = ai_study_supervisor(study_data)
    except Exception as e:
        return jsonify({"status": "fail", "message": str(e)}), 500

    return jsonify({"status": "success", "report": report, "study_data": study_data})


@app.route("/api/record_study", methods=['POST'])
@login_required
def record_study():
    """手动记录学习"""
    data = request.json
    course_id = data.get('course_id')
    study_minutes = data.get('study_minutes', 30)
    from datetime import date
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT INTO study_records (user_id, course_id, study_date, study_minutes, tasks_completed) VALUES (%s,%s,%s,%s,1)",
            (g.user_id, course_id, date.today(), study_minutes))
        db.commit()
        cursor.close()
        return jsonify({"status": "success", "message": "学习记录已保存"})
    except Exception as e:
        db.rollback()
        cursor.close()
        return jsonify({"status": "fail", "message": str(e)}), 500


# ==================== 10. 获取AI请求总次数 ====================
@app.route("/api/stats", methods=['GET'])
@login_required
def get_stats():
    """获取用户统计数据"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM courses WHERE user_id = %s", (g.user_id,))
    course_count = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM error_books WHERE user_id = %s", (g.user_id,))
    error_count = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM writings WHERE user_id = %s", (g.user_id,))
    writing_count = cursor.fetchone()['cnt']
    cursor.execute("SELECT COUNT(*) as cnt FROM ai_conversations WHERE user_id = %s", (g.user_id,))
    ai_count = cursor.fetchone()['cnt']
    cursor.close()
    return jsonify({
        "courses": course_count,
        "errors": error_count,
        "writings": writing_count,
        "ai_chats": ai_count // 2  # 一问一答算一次
    })


# ==================== 工具函数 ====================
def parse_learning_path(path_text):
    """解析AI返回的学习路径文本，提取步骤列表"""
    steps = []
    for line in path_text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        # 匹配 "1. xxx" "1、xxx" 等格式
        import re
        m = re.match(r'^(\d+)[\.、\)）]\s*(.+)', line)
        if m:
            desc = m.group(2).strip()
            if desc:
                steps.append(desc)
    return steps if steps else [path_text.strip()[:100]]


# ==================== 启动 ====================
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
