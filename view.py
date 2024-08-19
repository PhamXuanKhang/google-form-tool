import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

class GUI:
    def __init__(self, root):
        self.root = root

        # Điều chỉnh kích cỡ và thuộc tính giao diện
        self.root.title("AutoFill Google Forms")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        self.root.config(bg="#d3d3d3")

        # Tạo notebook để dễ dàng chuyển trang, notebook gồm 4 trang
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True)
        
        self.frame1 = ttk.Frame(self.notebook)
        self.frame2 = ttk.Frame(self.notebook)
        self.frame3 = ttk.Frame(self.notebook)

        self.notebook.add(self.frame1, text="Form Details")
        self.notebook.add(self.frame2, text="Page Details")
        self.notebook.add(self.frame3, text="Prefill Links")

        self.init_tab1()
        self.window_count = 90
    
    def init_tab1(self):
        # Số form cần điền
        ttk.Label(self.frame1, text="Number of forms:").grid(column=0, row=0, padx=10, pady=10, sticky='W')
        self.num_forms_entry = ttk.Entry(self.frame1)
        self.num_forms_entry.grid(column=1, row=0, padx=10, pady=10, sticky='W')

        # Số trang của form
        ttk.Label(self.frame1, text="Number of pages per form:").grid(column=0, row=1, padx=10, pady=10, sticky='W')
        self.num_pages_entry = ttk.Entry(self.frame1)
        self.num_pages_entry.grid(column=1, row=1, padx=10, pady=10, sticky='W')

        # Nút chuyển tiếp
        self.tab1_Next_button = ttk.Button(self.frame1, text="Next", command=self.open_new_window)
        self.tab1_Next_button.grid(column=2, row=2, padx=10, pady=10, sticky='W')

    # def init_tab2(self):
    #     self.notebook.select(self.frame2)
    #     self.num_forms_entry.config(state='disabled') # ngăn chỉnh sửa giá trị ở tab đã điền
    #     self.num_pages_entry.config(state='disabled')
    #     self.tab1_Next_button.config(state='disabled')

    #     # Lấy các giá trị vừa điền ở tab1
    #     try:
    #         self.num_forms = int(self.num_forms_entry.get())
    #         self.num_pages = int(self.num_pages_entry.get())
    #     except ValueError:
    #         messagebox.showerror("Input Error", "Please enter a valid number of pages.")

    def open_new_window(self):
        if self.window_count < 100:
            self.window_count += 1
            new_window = tk.Toplevel(self.root)
            new_window.title(f"Window {self.window_count}")
            new_window.geometry("300x200")

            label = ttk.Label(new_window, text=f"This is window {self.window_count}")
            label.pack(padx=20, pady=20)

            close_button = ttk.Button(new_window, text="Close", command=lambda: self.next_window(new_window))
            close_button.pack(pady=10)
        
    def next_window(self, current_window):
        current_window.destroy()
        self.open_new_window()

if __name__ == "__main__":
    root = tk.Tk()
    app = GUI(root)
    root.mainloop()