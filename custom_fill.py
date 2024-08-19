import random
from unidecode import unidecode

class Custom_fill:
    def __init__(self, num_forms):
        self.num_forms = num_forms      # Số form
        self.list_links = []
        self.list_emails = []
        self.list_names = []
        self.list_dates = []
        self.list_phones = []
        self.results = {}

        self.ho_list = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Phan", "Vũ", "Võ", "Đặng", "Bùi", "Đỗ", "Hồ", "Ngô", "Dương", "Lý", "Trịnh", "Lương", "Mai", "Tô", "Đinh", "Đào", "Vương", "Hà", "Thái"]
        self.ten_dem_list = ["Văn", "Thị", "Minh", "Đức", "Thành", "Tuấn", "Hữu", "Hoàng", "Thiện", "Như", "Kim", "Thu", "Ngọc", "Hải", "Quốc", "Gia", "Phương", "Thanh", "Bảo", "An", "Quyết", "Kiến", "Mỹ", "Duy", "Quỳnh"]
        self.ten_list = ["Anh", "Hương", "Nam", "Linh", "Hải", "Thảo", "Tùng", "Dương", "Thu", "Long", "Mai", "Hà", "Phong", "Trang", "Hoàng", "Lâm", "Bình", "Ngọc", "Thủy", "Trung", "Quang", "Lương", "Đăng", "Quốc", "Đạt"]
    
    ### Hàm tạo thông tin ###
    def gen_info(self, num_fpt_email = 0, feedback_list = dict(), num_empty_fb = False):
        # Tạo tên
        for _ in range(self.num_forms):
            ho = random.choice(self.ho_list)
            ten_dem = random.choice(self.ten_dem_list)
            ten = random.choice(self.ten_list)
            self.list_names.append(f"{ho} {ten_dem} {ten}")

        # Tạo email
        for name in self.list_names:
            arr = unidecode(name).split(" ")
            if num_fpt_email > 0:
                self.list_emails.append(f"{arr[2].lower()}{arr[1][0].lower()}{arr[0][0].lower()}{'he'}{random.choice(['18','17'])}{random.randint(0,9999)}@fpt.edu.vn")
                num_fpt_email -= 1
            else:
                self.list_emails.append(f"{arr[2]}{arr[1]}{arr[0][0]}{random.randint(0,9999)}@gmail.com")
        random.shuffle(self.list_names)

        # Tạo ngày
        for i in range(self.num_forms):
            self.list_dates.append(f"{random.randint(1999, 2005)}-{random.randint(1, 12)}-{random.randint(1, 28)}")

        # Tạo sđt
        for _ in range(self.num_forms):
            self.list_phones.append(f"09{random.randint(10000000, 99999999)}")

        # Tạo các loại điền khác (lời khuyên, góp ý)
        for key,value in feedback_list.items():
            self.results[key] = value
            for i in range(self.num_forms - len(value)):
                if num_empty_fb:
                    self.results[key].append("")
                else:
                    self.results[key].append(random.choice(value))
            random.shuffle(self.results[key])
        
        self.results.update({'list_names': self.list_names, 'list_emails': self.list_emails, 'list_dates': self.list_dates, 'list_phones': self.list_phones}) 
        return self.results