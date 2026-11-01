#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
=============================================================================
KIOTVIET CRM TO GOOGLE SHEETS SYNC HUB - MODERN GUI (CUSTOMTKINTER)
=============================================================================
Giao diện hiện đại v3.0 Pro hỗ trợ Dark/Light Mode, bo góc tinh tế,
quản lý đa nhiệm các cặp đồng bộ bộ lọc CRM ra Google Sheets.
=============================================================================
"""

import os
import sys
import json
import time
import re
import threading
from datetime import datetime

import customtkinter as ctk
from tkinter import messagebox

# Cấu hình đường dẫn và module
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from crm_export_tool import (
    export_crm_data,
    push_to_google_sheets,
    save_to_excel,
    find_credentials,
    find_cookie,
    clean_excel_cell
)

CONFIG_FILE = os.path.join(CURRENT_DIR, "tasks_config.json")
COOKIE_FILE = os.path.join(CURRENT_DIR, "cookie.txt")

# Thiết lập theme mặc định
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ModernCrmSyncApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("KiotViet CRM ➔ Google Sheets Sync Hub Pro v3.0")
        self.geometry("1100x860")
        self.minsize(980, 720)

        self.pair_rows = []
        self.is_running = False

        self._build_modern_ui()
        self._load_initial_data()

    def _build_modern_ui(self):
        # =====================================================================
        # 1. HEADER BAR
        # =====================================================================
        header_card = ctk.CTkFrame(self, corner_radius=0, fg_color=("#e2e8f0", "#1e293b"), height=70)
        header_card.pack(fill="x", side="top")
        header_card.pack_propagate(False)

        # Title & Logo
        left_header = ctk.CTkFrame(header_card, fg_color="transparent")
        left_header.pack(side="left", padx=20, pady=10)

        badge_lbl = ctk.CTkLabel(
            left_header,
            text="KV CRM",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color="#2563eb",
            text_color="#ffffff",
            corner_radius=6,
            padx=8,
            pady=4
        )
        badge_lbl.pack(side="left", padx=(0, 10))

        title_box = ctk.CTkFrame(left_header, fg_color="transparent")
        title_box.pack(side="left")

        app_title = ctk.CTkLabel(
            title_box,
            text="KiotViet CRM ➔ Google Sheets Sync Hub",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            anchor="w"
        )
        app_title.pack(anchor="w")

        app_sub = ctk.CTkLabel(
            title_box,
            text="Hệ thống tự động trích xuất bộ lọc CRM và đồng bộ đa nhiệm | 100% Read-Only",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748b", "#94a3b8"),
            anchor="w"
        )
        app_sub.pack(anchor="w")

        # Right Controls: Theme Switch & Version Badge
        right_header = ctk.CTkFrame(header_card, fg_color="transparent")
        right_header.pack(side="right", padx=20, pady=10)

        self.theme_switch = ctk.CTkSwitch(
            right_header,
            text="Giao diện Tối",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self._toggle_theme,
            onvalue="dark",
            offvalue="light"
        )
        self.theme_switch.select()
        self.theme_switch.pack(side="left", padx=10)

        ver_badge = ctk.CTkLabel(
            right_header,
            text="v3.0 Pro",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color=("#cbd5e1", "#334155"),
            text_color=("#334155", "#94a3b8"),
            corner_radius=12,
            padx=8,
            pady=2
        )
        ver_badge.pack(side="left")

        # Main Scrollable Body Container
        self.main_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        self.main_scroll.pack(fill="both", expand=True, padx=20, pady=15)

        # =====================================================================
        # 2. CARD: QUẢN LÝ COOKIE PHIÊN LÀM VIỆC
        # =====================================================================
        cookie_card = ctk.CTkFrame(self.main_scroll, corner_radius=12, fg_color=("#ffffff", "#1e293b"), border_width=1, border_color=("#e2e8f0", "#334155"))
        cookie_card.pack(fill="x", pady=(0, 15), padx=2)

        cookie_head = ctk.CTkFrame(cookie_card, fg_color="transparent")
        cookie_head.pack(fill="x", padx=16, pady=(14, 8))

        ctk.CTkLabel(
            cookie_head,
            text="🔑 1. Phiên Đăng Nhập CRM (Session Cookie)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        ).pack(side="left")

        self.cookie_badge = ctk.CTkLabel(
            cookie_head,
            text="🟡 Đang kiểm tra...",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            fg_color=("#fef3c7", "#78350f"),
            text_color=("#d97706", "#fde68a"),
            corner_radius=6,
            padx=10,
            pady=2
        )
        self.cookie_badge.pack(side="left", padx=12)

        # Cookie action buttons
        btn_paste = ctk.CTkButton(
            cookie_head,
            text="📋 Dán từ Clipboard",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=("#f1f5f9", "#334155"),
            hover_color=("#e2e8f0", "#475569"),
            text_color=("#0f172a", "#f8fafc"),
            width=130,
            height=28,
            corner_radius=6,
            command=self._paste_cookie
        )
        btn_paste.pack(side="right", padx=(6, 0))

        btn_save = ctk.CTkButton(
            cookie_head,
            text="💾 Lưu Cookie",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=("#f1f5f9", "#334155"),
            hover_color=("#e2e8f0", "#475569"),
            text_color=("#0f172a", "#f8fafc"),
            width=90,
            height=28,
            corner_radius=6,
            command=self._save_cookie
        )
        btn_save.pack(side="right")

        self.cookie_textbox = ctk.CTkTextbox(
            cookie_card,
            height=70,
            font=ctk.CTkFont(family="Consolas", size=10),
            corner_radius=8,
            fg_color=("#f8fafc", "#0f172a"),
            border_width=1,
            border_color=("#cbd5e1", "#334155")
        )
        self.cookie_textbox.pack(fill="x", padx=16, pady=(0, 14))
        self.cookie_textbox.bind("<KeyRelease>", lambda e: self._validate_cookie_text())

        # =====================================================================
        # 3. CARD: QUẢN LÝ CÁC CẶP [LINK CRM] ➔ [LINK GG SHEET]
        # =====================================================================
        pairs_card = ctk.CTkFrame(self.main_scroll, corner_radius=12, fg_color=("#ffffff", "#1e293b"), border_width=1, border_color=("#e2e8f0", "#334155"))
        pairs_card.pack(fill="both", expand=True, pady=(0, 15), padx=2)

        pairs_head = ctk.CTkFrame(pairs_card, fg_color="transparent")
        pairs_head.pack(fill="x", padx=16, pady=(14, 10))

        ctk.CTkLabel(
            pairs_head,
            text="📋 2. Danh Sách Các Cặp Cần Đồng Bộ",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        ).pack(side="left")

        self.pair_count_lbl = ctk.CTkLabel(
            pairs_head,
            text="0 tác vụ",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("#64748b", "#94a3b8")
        )
        self.pair_count_lbl.pack(side="left", padx=10)

        btn_add = ctk.CTkButton(
            pairs_head,
            text="➕ Thêm Cặp Mới",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            text_color="#ffffff",
            width=135,
            height=30,
            corner_radius=6,
            command=lambda: self.add_pair_row()
        )
        btn_add.pack(side="right")

        # Header columns title
        col_header = ctk.CTkFrame(pairs_card, fg_color=("#f1f5f9", "#0f172a"), height=30, corner_radius=6)
        col_header.pack(fill="x", padx=16, pady=(0, 6))

        ctk.CTkLabel(col_header, text="Bật", width=42, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), anchor="center").pack(side="left", padx=4)
        ctk.CTkLabel(col_header, text="#", width=28, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), anchor="center").pack(side="left", padx=2)
        ctk.CTkLabel(col_header, text="Link Bộ Lọc CRM (URL)", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), anchor="w").pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkLabel(col_header, text="Link Google Sheets (URL)", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), anchor="w").pack(side="left", fill="x", expand=True, padx=6)
        ctk.CTkLabel(col_header, text="Tên Tab", width=130, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), anchor="center").pack(side="left", padx=4)
        ctk.CTkLabel(col_header, text="Trạng Thái", width=115, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), anchor="center").pack(side="left", padx=4)
        ctk.CTkLabel(col_header, text="Xóa", width=45, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), anchor="center").pack(side="left", padx=(4, 8))

        # Dynamic rows container
        self.rows_frame = ctk.CTkFrame(pairs_card, fg_color="transparent")
        self.rows_frame.pack(fill="both", expand=True, padx=16, pady=(0, 14))

        # =====================================================================
        # 4. CARD: ĐIỀU KHIỂN & CONSOLE LOG
        # =====================================================================
        action_card = ctk.CTkFrame(self.main_scroll, corner_radius=12, fg_color=("#ffffff", "#1e293b"), border_width=1, border_color=("#e2e8f0", "#334155"))
        action_card.pack(fill="x", pady=(0, 10), padx=2)

        ctrl_row = ctk.CTkFrame(action_card, fg_color="transparent")
        ctrl_row.pack(fill="x", padx=16, pady=(12, 8))

        self.save_excel_var = ctk.BooleanVar(value=True)
        self.chk_excel = ctk.CTkCheckBox(
            ctrl_row,
            text="💾 Tự động lưu bản sao file Excel (.xlsx) về máy",
            variable=self.save_excel_var,
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.chk_excel.pack(side="left")

        self.btn_run = ctk.CTkButton(
            ctrl_row,
            text="🚀 BẮT ĐẦU CHẠY ĐỒNG BỘ TẤT CẢ",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            fg_color="#16a34a",
            hover_color="#15803d",
            text_color="#ffffff",
            height=38,
            corner_radius=8,
            command=self.start_sync_thread
        )
        self.btn_run.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(action_card, height=8, corner_radius=4)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 10))

        # Log Terminal
        log_box = ctk.CTkFrame(action_card, fg_color="transparent")
        log_box.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkLabel(
            log_box,
            text="📝 Nhật Ký Thực Thi (Console Log)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color=("#64748b", "#94a3b8")
        ).pack(anchor="w", pady=(0, 4))

        self.log_text = ctk.CTkTextbox(
            log_box,
            height=120,
            font=ctk.CTkFont(family="Consolas", size=10),
            corner_radius=8,
            fg_color=("#0f172a", "#020617"),
            text_color="#38bdf8",
            border_width=1,
            border_color=("#1e293b", "#1e293b")
        )
        self.log_text.pack(fill="x")

    # =========================================================================
    # THEME TOGGLE
    # =========================================================================
    def _toggle_theme(self):
        mode = self.theme_switch.get()
        ctk.set_appearance_mode(mode)
        if mode == "dark":
            self.theme_switch.configure(text="Giao diện Tối")
        else:
            self.theme_switch.configure(text="Giao diện Sáng")

    # =========================================================================
    # COOKIE MANAGEMENT
    # =========================================================================
    def _validate_cookie_text(self):
        c_str = self.cookie_textbox.get("1.0", "end").strip()
        has_session = ("KVCRM_PHPSESSID" in c_str or "kvcrm_phpsessid" in c_str or "PHPSESSID" in c_str)
        has_user = ("current_user" in c_str)

        if has_session and has_user:
            m = re.search(r'current_user=(\d+)', c_str)
            user_id = m.group(1) if m else "11216"
            self.cookie_badge.configure(
                text=f"🟢 ĐÃ KẾT NỐI (User: {user_id} | Session: Đầy đủ)",
                fg_color=("#dcfce7", "#064e3b"),
                text_color=("#15803d", "#6ee7b7")
            )
            return True
        elif has_session:
            self.cookie_badge.configure(
                text="🟡 CÓ PHPSESSID (Khuyên dùng: Đăng nhập để có User)",
                fg_color=("#fef3c7", "#78350f"),
                text_color=("#d97706", "#fde68a")
            )
            return True
        elif c_str:
            self.cookie_badge.configure(
                text="🔴 THIẾU PHPSESSID (Cần mở CRM lấy lại bằng Extension)",
                fg_color=("#fee2e2", "#7f1d1d"),
                text_color=("#b91c1c", "#fca5a5")
            )
            return False
        else:
            self.cookie_badge.configure(
                text="⚪ Chưa nhập Cookie",
                fg_color=("#f1f5f9", "#334155"),
                text_color=("#64748b", "#94a3b8")
            )
            return False

    def _paste_cookie(self):
        try:
            clip = self.clipboard_get().strip()
            if clip:
                self.cookie_textbox.delete("1.0", "end")
                self.cookie_textbox.insert("1.0", clip)
                self._validate_cookie_text()
                self.log("📋 Đã dán Cookie mới từ Clipboard!")
        except Exception:
            messagebox.showwarning("Clipboard", "Không đọc được dữ liệu từ Clipboard.")

    def _save_cookie(self):
        c_str = self.cookie_textbox.get("1.0", "end").strip()
        if not c_str:
            messagebox.showwarning("Cảnh báo", "Ô Cookie đang trống!")
            return
        try:
            with open(COOKIE_FILE, "w", encoding="utf-8") as f:
                f.write(c_str)
            parent_cookie = os.path.join(os.path.dirname(CURRENT_DIR), "cookie.txt")
            if os.path.exists(os.path.dirname(parent_cookie)):
                try:
                    with open(parent_cookie, "w", encoding="utf-8") as pf:
                        pf.write(c_str)
                except:
                    pass
            self.log(f"💾 Đã lưu Cookie vào {COOKIE_FILE}")
            messagebox.showinfo("Thành công", "Đã lưu Cookie làm mặc định thành công!")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu file: {e}")

    def _load_cookie(self):
        c = find_cookie()
        if c:
            self.cookie_textbox.delete("1.0", "end")
            self.cookie_textbox.insert("1.0", c)
            self._validate_cookie_text()
            self.log("🔑 Đã nạp Cookie tự động từ hệ thống.")

    # =========================================================================
    # DYNAMIC ROWS MANAGEMENT
    # =========================================================================
    def add_pair_row(self, crm_url="", gsheet_url="", tab_name="", enabled=True):
        row_idx = len(self.pair_rows) + 1

        row_card = ctk.CTkFrame(
            self.rows_frame,
            corner_radius=8,
            fg_color=("#f8fafc", "#0f172a") if enabled else ("#f1f5f9", "#020617"),
            border_width=1,
            border_color=("#e2e8f0", "#1e293b")
        )
        row_card.pack(fill="x", pady=4)

        # Công tắc Bật/Tắt từng cặp
        switch_var = ctk.BooleanVar(value=enabled)
        switch_btn = ctk.CTkSwitch(
            row_card,
            text="",
            variable=switch_var,
            width=38,
            switch_width=34,
            switch_height=18,
            progress_color="#10b981",
            command=lambda: self._on_switch_toggled(row_data)
        )
        switch_btn.pack(side="left", padx=(8, 2), pady=6)

        lbl_idx = ctk.CTkLabel(
            row_card,
            text=f"#{row_idx}",
            width=28,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold")
        )
        lbl_idx.pack(side="left", padx=2, pady=6)

        entry_crm = ctk.CTkEntry(
            row_card,
            placeholder_text="https://kvcrm.kiotviet.vn/index.php?module=...&viewname=...",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            height=30,
            corner_radius=6
        )
        entry_crm.pack(side="left", fill="x", expand=True, padx=4, pady=6)
        if crm_url:
            entry_crm.insert(0, crm_url)

        entry_gsheet = ctk.CTkEntry(
            row_card,
            placeholder_text="https://docs.google.com/spreadsheets/d/.../edit?gid=...#gid=...",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            height=30,
            corner_radius=6
        )
        entry_gsheet.pack(side="left", fill="x", expand=True, padx=4, pady=6)
        if gsheet_url:
            entry_gsheet.insert(0, gsheet_url)

        entry_tab = ctk.CTkEntry(
            row_card,
            placeholder_text="(Tự động theo link)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            width=130,
            height=30,
            corner_radius=6
        )
        entry_tab.pack(side="left", padx=4, pady=6)
        if tab_name and tab_name not in ["(Tự động theo link)", "(Tự động)"]:
            entry_tab.insert(0, tab_name)

        status_text = "⏳ Sẵn sàng" if enabled else "⏸️ Đã tắt"
        status_color = ("#64748b", "#94a3b8") if enabled else ("#94a3b8", "#64748b")
        lbl_status = ctk.CTkLabel(
            row_card,
            text=status_text,
            width=115,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=status_color
        )
        lbl_status.pack(side="left", padx=4, pady=6)

        row_data = {
            "card": row_card,
            "switch_var": switch_var,
            "switch_btn": switch_btn,
            "lbl_idx": lbl_idx,
            "entry_crm": entry_crm,
            "entry_gsheet": entry_gsheet,
            "entry_tab": entry_tab,
            "lbl_status": lbl_status
        }

        btn_del = ctk.CTkButton(
            row_card,
            text="🗑️",
            width=36,
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color=("#fee2e2", "#450a0a"),
            hover_color=("#fecaca", "#7f1d1d"),
            text_color=("#dc2626", "#f87171"),
            corner_radius=6,
            command=lambda r=row_data: self.remove_pair_row(r)
        )
        btn_del.pack(side="left", padx=(4, 8), pady=6)

        self.pair_rows.append(row_data)
        self._refresh_indices()

    def _on_switch_toggled(self, row_data):
        is_on = row_data["switch_var"].get()
        if is_on:
            row_data["lbl_status"].configure(text="⏳ Sẵn sàng", text_color=("#64748b", "#94a3b8"))
            row_data["card"].configure(fg_color=("#f8fafc", "#0f172a"))
        else:
            row_data["lbl_status"].configure(text="⏸️ Đã tắt", text_color=("#94a3b8", "#64748b"))
            row_data["card"].configure(fg_color=("#f1f5f9", "#020617"))
        self._refresh_indices()
        self._save_config()

    def remove_pair_row(self, row_data):
        if len(self.pair_rows) <= 1:
            row_data["entry_crm"].delete(0, "end")
            row_data["entry_gsheet"].delete(0, "end")
            row_data["entry_tab"].delete(0, "end")
            row_data["lbl_status"].configure(text="⏳ Sẵn sàng", text_color=("#64748b", "#94a3b8"))
            return

        row_data["card"].destroy()
        self.pair_rows.remove(row_data)
        self._refresh_indices()
        self._save_config()

    def _refresh_indices(self):
        active_count = sum(1 for r in self.pair_rows if r["switch_var"].get())
        total_count = len(self.pair_rows)
        for idx, row in enumerate(self.pair_rows, start=1):
            row["lbl_idx"].configure(text=f"#{idx}")
        self.pair_count_lbl.configure(text=f"{active_count}/{total_count} tác vụ đang bật")
        if not self.is_running:
            if active_count > 0:
                self.btn_run.configure(text=f"🚀 BẮT ĐẦU CHẠY ({active_count} CẶP ĐANG BẬT)", state="normal", fg_color="#16a34a")
            else:
                self.btn_run.configure(text="⚠️ CHƯA BẬT CẶP NÀO", state="disabled", fg_color="#64748b")

    def _save_config(self):
        tasks = []
        for r in self.pair_rows:
            crm = r["entry_crm"].get().strip()
            gsheet = r["entry_gsheet"].get().strip()
            tab = r["entry_tab"].get().strip()
            enabled = bool(r["switch_var"].get())
            if tab == "(Tự động theo link)":
                tab = ""
            if crm or gsheet:
                tasks.append({
                    "enabled": enabled,
                    "crm_url": crm,
                    "gsheet_url": gsheet,
                    "tab_name": tab
                })
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(tasks, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_initial_data(self):
        self._load_cookie()

        tasks = []
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    tasks = json.load(f)
            except Exception:
                pass

        if tasks and isinstance(tasks, list):
            for t in tasks:
                self.add_pair_row(
                    crm_url=t.get("crm_url", ""),
                    gsheet_url=t.get("gsheet_url", ""),
                    tab_name=t.get("tab_name", ""),
                    enabled=t.get("enabled", True)
                )
        else:
            # Default pairs
            self.add_pair_row(
                crm_url="https://kvcrm.kiotviet.vn/index.php?module=CSKHSC&parent=&page=1&view=List&viewname=17629&orderby=&sortorder=&search_params=%5B%5B%5B%22thoi_gian_checkin%22%2C%22bw%22%2C%222026-09-01%2C2026-09-30%22%5D%5D%5D",
                gsheet_url="https://docs.google.com/spreadsheets/d/1DLBiD2kPO6Piw0kapG5W3quIEdc0XdVhRON4F8sxsi0/edit?gid=0#gid=0",
                tab_name="",
                enabled=True
            )

        self.log("✅ Giao diện Pro v3.0 đã sẵn sàng. Chúc bạn một ngày làm việc hiệu quả!")

    # =========================================================================
    # EXECUTION & LOGGING
    # =========================================================================
    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {msg}\n")
        self.log_text.see("end")

    def start_sync_thread(self):
        if self.is_running:
            messagebox.showwarning("Thông báo", "Tiến trình đồng bộ đang chạy, vui lòng chờ!")
            return

        cookie_str = self.cookie_textbox.get("1.0", "end").strip()
        if not cookie_str:
            messagebox.showerror("Lỗi", "Vui lòng nhập hoặc dán Cookie CRM trước khi chạy!")
            return

        cred_file = find_credentials()
        if not cred_file:
            messagebox.showerror(
                "Lỗi Credentials",
                "Không tìm thấy file credentials.json của Service Account!\nVui lòng đảm bảo file credentials.json nằm trong thư mục."
            )
            return

        self._save_config()
        self._save_cookie()

        valid_tasks = []
        for idx, r in enumerate(self.pair_rows):
            if not r["switch_var"].get():
                r["lbl_status"].configure(text="⏸️ Đã bỏ qua", text_color=("#94a3b8", "#64748b"))
                continue

            crm = r["entry_crm"].get().strip()
            gsheet = r["entry_gsheet"].get().strip()
            tab = r["entry_tab"].get().strip()
            if tab in ["(Tự động theo link)", "(Tự động)", "Sheet1"]:
                if "gid=" in gsheet:
                    tab = ""
            if crm and gsheet:
                valid_tasks.append((idx, r, crm, gsheet, tab))
            elif crm or gsheet:
                r["lbl_status"].configure(text="⚠️ Thiếu link", text_color="#d97706")

        if not valid_tasks:
            messagebox.showwarning("Cảnh báo", "Không có tác vụ nào đang BẬT hoặc hợp lệ để chạy!\nVui lòng bật công tắc ít nhất 1 cặp tác vụ.")
            return

        self.is_running = True
        self.btn_run.configure(state="disabled", fg_color="#64748b", text="⏳ ĐANG ĐỒNG BỘ DỮ LIỆU...")
        self.progress_bar.set(0)

        t = threading.Thread(
            target=self._run_worker,
            args=(cookie_str, cred_file, valid_tasks, self.save_excel_var.get()),
            daemon=True
        )
        t.start()

    def _run_worker(self, cookie_str, cred_file, tasks, save_excel):
        total = len(tasks)
        success_count = 0
        self.after(0, lambda: self.log(f"🚀 BẮT ĐẦU ĐỒNG BỘ {total} CẶP TÁC VỤ..."))

        for i, (row_idx, row_obj, crm_url, gsheet_url, tab_name) in enumerate(tasks, start=1):
            self.after(0, lambda r=row_obj: r["lbl_status"].configure(text="🔄 Đang kéo...", text_color="#0284c7"))
            self.after(0, lambda idx=i: self.log(f"--- [Tác vụ {idx}/{total}] Đang kết nối CRM... ---"))

            try:
                # 1. Trích xuất CRM
                rows = export_crm_data(cookie_str, crm_url)
                if not rows or len(rows) < 1 or rows == [['Invalid request']]:
                    raise ValueError("Không lấy được dữ liệu. Cookie hết hạn hoặc sai bộ lọc.")

                total_records = len(rows) - 1
                self.after(0, lambda rec=total_records: self.log(f"  ✓ Lấy được {rec} dòng dữ liệu từ CRM."))

                # 2. Đẩy lên Google Sheets
                self.after(0, lambda: self.log(f"  📄 Đang đẩy vào Google Sheets..."))
                ok = push_to_google_sheets(rows, cred_file, gsheet_url, worksheet_name=tab_name)

                if ok:
                    if save_excel:
                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        excel_file = os.path.join(CURRENT_DIR, f"CRM_Export_Task_{i}_{ts}.xlsx")
                        save_to_excel(rows, excel_file)
                        self.after(0, lambda ef=excel_file: self.log(f"  💾 Đã lưu bản sao Excel: {os.path.basename(ef)}"))

                    success_count += 1
                    self.after(0, lambda r=row_obj, rec=total_records: r["lbl_status"].configure(
                        text=f"✅ {rec} dòng", text_color="#16a34a"
                    ))
                    self.after(0, lambda idx=i: self.log(f"  🎉 [Tác vụ {idx}/{total}] ĐỒNG BỘ THÀNH CÔNG!"))
                else:
                    raise ValueError("Lỗi khi ghi dữ liệu lên Google Sheets.")

            except Exception as ex:
                err_msg = str(ex)
                self.after(0, lambda r=row_obj: r["lbl_status"].configure(text="❌ Thất bại", text_color="#dc2626"))
                self.after(0, lambda idx=i, em=err_msg: self.log(f"  ❌ [Tác vụ {idx}/{total}] THẤT BẠI: {em}"))

            progress = (i / total)
            self.after(0, lambda p=progress: self.progress_bar.set(p))
            time.sleep(0.5)

        self.after(0, self._on_worker_finished, success_count, total)

    def _on_worker_finished(self, success_count, total):
        self.is_running = False
        self.btn_run.configure(state="normal", fg_color="#16a34a", text="🚀 BẮT ĐẦU CHẠY ĐỒNG BỘ TẤT CẢ")
        self.log(f"🏁 HOÀN TẤT ĐỢT ĐỒNG BỘ: {success_count}/{total} tác vụ thành công.")

        if success_count == total:
            messagebox.showinfo("Hoàn Tất", f"Đã đồng bộ thành công toàn bộ {total}/{total} cặp tác vụ lên Google Sheets!")
        else:
            messagebox.showwarning("Hoàn Tất", f"Đồng bộ xong: {success_count}/{total} thành công. Vui lòng kiểm tra log lỗi.")

def main():
    app = ModernCrmSyncApp()
    app.mainloop()

if __name__ == "__main__":
    main()
