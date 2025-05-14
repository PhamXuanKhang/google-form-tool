from flask import Blueprint, render_template, request, redirect, url_for

bp = Blueprint('main', __name__)

@bp.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@bp.route('/extract', methods=['POST'])
def extract():
    form_url = request.form['url']
    # Giả lập dữ liệu form (sẽ thay bằng logic trích xuất thật sau)
    form_data = [
        {
            'question': 'What is your favorite color?',
            'type': 'multiple_choice',
            'options': ['Red', 'Blue', 'Green'],
            'percentages': [0, 0, 0]  # Tỷ lệ mặc định
        },
        {
            'question': 'How often do you exercise?',
            'type': 'dropdown',
            'options': ['Daily', 'Weekly', 'Rarely'],
            'percentages': [0, 0, 0]
        },
        {
            'question': 'Describe your experience',
            'type': 'text',
            'options': [],  # Không có đáp án, sẽ dùng Gemini API sau
            'percentages': []
        }
    ]
    return render_template('results.html', form_data=form_data)

@bp.route('/edit', methods=['POST'])
def edit():
    form_data = request.form.to_dict()
    # Logic xử lý tỷ lệ đáp án và gọi Gemini API sẽ được thêm sau
    return redirect(url_for('main.progress'))  # Chuyển hướng đến trang tiến trình (chưa có)

@bp.route('/progress', methods=['GET'])
def progress():
    return "Progress page (to be implemented)"  # Placeholder