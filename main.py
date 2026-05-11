import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw
import os
import json

class OCRLabelingTool:
    def __init__(self, root):
        self.root = root
        self.root.title("OCR Image Labeling Tool")
        self.root.geometry("1400x900")
        self.root.configure(bg="#1e1e2e")

        # State variables
        self.image_list = []
        self.current_image_index = -1
        self.current_image = None
        self.original_image = None
        self.photo_image = None
        self.labels = {}  # {image_path: [{bbox, text, id}]}
        self.label_counter = 0

        # Drawing state
        self.start_x = None
        self.start_y = None
        self.current_rect = None
        self.is_drawing = False
        self.selected_label_id = None

        # Scale factors
        self.scale_x = 1.0
        self.scale_y = 1.0

        # Colors
        self.colors = {
            "bg": "#1e1e2e",
            "panel": "#2a2a3e",
            "accent": "#7c3aed",
            "accent_hover": "#6d28d9",
            "success": "#10b981",
            "danger": "#ef4444",
            "warning": "#f59e0b",
            "text": "#e2e8f0",
            "text_dim": "#94a3b8",
            "border": "#374151",
            "rect_default": "#7c3aed",
            "rect_selected": "#f59e0b",
            "canvas_bg": "#0f0f1a",
        }

        self.setup_ui()
        self.setup_bindings()

    def setup_ui(self):
        # ── Top Bar ──────────────────────────────────────────────────
        top_bar = tk.Frame(self.root, bg=self.colors["panel"], height=60)
        top_bar.pack(fill=tk.X, side=tk.TOP)
        top_bar.pack_propagate(False)

        title = tk.Label(
            top_bar, text="🏷  OCR Labeling Tool",
            font=("Segoe UI", 16, "bold"),
            bg=self.colors["panel"], fg=self.colors["accent"]
        )
        title.pack(side=tk.LEFT, padx=20, pady=10)

        btn_frame = tk.Frame(top_bar, bg=self.colors["panel"])
        btn_frame.pack(side=tk.RIGHT, padx=10, pady=8)

        self.make_button(btn_frame, "📁  Add Images", self.add_images,
                         self.colors["accent"]).pack(side=tk.LEFT, padx=4)
        self.make_button(btn_frame, "💾  Save All", self.save_all_labels,
                         self.colors["success"]).pack(side=tk.LEFT, padx=4)
        self.make_button(btn_frame, "📂  Load Session", self.load_session,
                         self.colors["warning"]).pack(side=tk.LEFT, padx=4)
        self.make_button(btn_frame, "🗑  Clear All", self.clear_all,
                         self.colors["danger"]).pack(side=tk.LEFT, padx=4)

        # ── Main Layout ───────────────────────────────────────────────
        main_frame = tk.Frame(self.root, bg=self.colors["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel – file list
        left_panel = tk.Frame(main_frame, bg=self.colors["panel"],
                               width=220, relief=tk.FLAT)
        left_panel.pack(side=tk.LEFT, fill=tk.Y)
        left_panel.pack_propagate(False)

        tk.Label(left_panel, text="Image Files",
                 font=("Segoe UI", 11, "bold"),
                 bg=self.colors["panel"], fg=self.colors["text"]
                 ).pack(pady=(15, 5), padx=10, anchor="w")

        self.file_count_label = tk.Label(
            left_panel, text="0 files loaded",
            font=("Segoe UI", 9), bg=self.colors["panel"],
            fg=self.colors["text_dim"]
        )
        self.file_count_label.pack(padx=10, anchor="w")

        list_frame = tk.Frame(left_panel, bg=self.colors["panel"])
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        scrollbar = tk.Scrollbar(list_frame, bg=self.colors["panel"])
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.file_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            bg=self.colors["bg"], fg=self.colors["text"],
            selectbackground=self.colors["accent"],
            selectforeground="white",
            font=("Segoe UI", 9),
            relief=tk.FLAT, borderwidth=0,
            activestyle="none"
        )
        self.file_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.file_listbox.yview)
        self.file_listbox.bind("<<ListboxSelect>>", self.on_file_select)

        # Navigation buttons
        nav_frame = tk.Frame(left_panel, bg=self.colors["panel"])
        nav_frame.pack(fill=tk.X, padx=8, pady=(0, 8))
        self.make_button(nav_frame, "◀ Prev", self.prev_image,
                         self.colors["border"]).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.make_button(nav_frame, "Next ▶", self.next_image,
                         self.colors["border"]).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Centre – canvas
        centre = tk.Frame(main_frame, bg=self.colors["bg"])
        centre.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        canvas_toolbar = tk.Frame(centre, bg=self.colors["panel"], height=40)
        canvas_toolbar.pack(fill=tk.X)
        canvas_toolbar.pack_propagate(False)

        self.image_name_label = tk.Label(
            canvas_toolbar, text="No image selected",
            font=("Segoe UI", 10), bg=self.colors["panel"],
            fg=self.colors["text_dim"]
        )
        self.image_name_label.pack(side=tk.LEFT, padx=15, pady=8)

        self.zoom_label = tk.Label(
            canvas_toolbar, text="Zoom: 100%",
            font=("Segoe UI", 9), bg=self.colors["panel"],
            fg=self.colors["text_dim"]
        )
        self.zoom_label.pack(side=tk.RIGHT, padx=15, pady=8)

        self.mode_label = tk.Label(
            canvas_toolbar, text="✏  Draw Mode",
            font=("Segoe UI", 9, "bold"), bg=self.colors["panel"],
            fg=self.colors["accent"]
        )
        self.mode_label.pack(side=tk.RIGHT, padx=10, pady=8)

        # Canvas with scrollbars
        canvas_frame = tk.Frame(centre, bg=self.colors["canvas_bg"])
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.h_scroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.v_scroll = tk.Scrollbar(canvas_frame)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas = tk.Canvas(
            canvas_frame,
            bg=self.colors["canvas_bg"],
            cursor="crosshair",
            relief=tk.FLAT,
            xscrollcommand=self.h_scroll.set,
            yscrollcommand=self.v_scroll.set
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)

        # Right panel – labels
        right_panel = tk.Frame(main_frame, bg=self.colors["panel"], width=300)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y)
        right_panel.pack_propagate(False)

        tk.Label(right_panel, text="Labels",
                 font=("Segoe UI", 11, "bold"),
                 bg=self.colors["panel"], fg=self.colors["text"]
                 ).pack(pady=(15, 5), padx=10, anchor="w")

        self.label_count_label = tk.Label(
            right_panel, text="0 labels",
            font=("Segoe UI", 9), bg=self.colors["panel"],
            fg=self.colors["text_dim"]
        )
        self.label_count_label.pack(padx=10, anchor="w")

        # Label input area
        input_card = tk.Frame(right_panel, bg=self.colors["bg"],
                               relief=tk.FLAT, bd=1)
        input_card.pack(fill=tk.X, padx=10, pady=10)

        tk.Label(input_card, text="Label Text:",
                 font=("Segoe UI", 9, "bold"),
                 bg=self.colors["bg"], fg=self.colors["text_dim"]
                 ).pack(anchor="w", padx=10, pady=(8, 2))

        self.label_entry = tk.Entry(
            input_card,
            font=("Segoe UI", 11),
            bg=self.colors["panel"], fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief=tk.FLAT, bd=8
        )
        self.label_entry.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.label_entry.bind("<Return>", self.confirm_label)

        btn_row = tk.Frame(input_card, bg=self.colors["bg"])
        btn_row.pack(fill=tk.X, padx=10, pady=(0, 8))
        self.make_button(btn_row, "✔ Confirm", self.confirm_label,
                         self.colors["success"], font_size=9
                         ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        self.make_button(btn_row, "✘ Cancel", self.cancel_label,
                         self.colors["danger"], font_size=9
                         ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Labels list
        lbl_list_frame = tk.Frame(right_panel, bg=self.colors["panel"])
        lbl_list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        lbl_scroll = tk.Scrollbar(lbl_list_frame)
        lbl_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.labels_listbox = tk.Listbox(
            lbl_list_frame,
            yscrollcommand=lbl_scroll.set,
            bg=self.colors["bg"], fg=self.colors["text"],
            selectbackground=self.colors["warning"],
            selectforeground="#000",
            font=("Segoe UI", 9),
            relief=tk.FLAT, borderwidth=0,
            activestyle="none"
        )
        self.labels_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lbl_scroll.config(command=self.labels_listbox.yview)
        self.labels_listbox.bind("<<ListboxSelect>>", self.on_label_select)

        # Label action buttons
        lbl_btn_frame = tk.Frame(right_panel, bg=self.colors["panel"])
        lbl_btn_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        self.make_button(lbl_btn_frame, "✏ Edit", self.edit_label,
                         self.colors["warning"], font_size=9
                         ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.make_button(lbl_btn_frame, "🗑 Delete", self.delete_label,
                         self.colors["danger"], font_size=9
                         ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        self.make_button(lbl_btn_frame, "💾 Export", self.export_current,
                         self.colors["success"], font_size=9
                         ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        # Status bar
        self.status_bar = tk.Label(
            self.root,
            text="Ready. Add images to start labeling.",
            font=("Segoe UI", 9),
            bg=self.colors["panel"], fg=self.colors["text_dim"],
            anchor="w", padx=15
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, ipady=5)

        # Pending rectangle (waiting for label text)
        self.pending_bbox = None

    # ── Helper ─────────────────────────────────────────────────────────────
    def make_button(self, parent, text, command, color, font_size=10):
        btn = tk.Button(
            parent, text=text, command=command,
            bg=color, fg="white",
            font=("Segoe UI", font_size, "bold"),
            relief=tk.FLAT, bd=0,
            padx=10, pady=5,
            cursor="hand2",
            activebackground=color, activeforeground="white"
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=self._lighten(color)))
        btn.bind("<Leave>", lambda e: btn.config(bg=color))
        return btn

    def _lighten(self, hex_color):
        """Return a slightly lighter version of a hex color."""
        try:
            h = hex_color.lstrip("#")
            r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
            r = min(255, r + 30)
            g = min(255, g + 30)
            b = min(255, b + 30)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color

    def set_status(self, msg):
        self.status_bar.config(text=msg)

    # ── Bindings ───────────────────────────────────────────────────────────
    def setup_bindings(self):
        self.canvas.bind("<ButtonPress-1>",   self.on_mouse_press)
        self.canvas.bind("<B1-Motion>",        self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>",  self.on_mouse_release)
        self.root.bind("<Delete>",             lambda e: self.delete_label())
        self.root.bind("<Left>",               lambda e: self.prev_image())
        self.root.bind("<Right>",              lambda e: self.next_image())
        self.root.bind("<Control-s>",          lambda e: self.save_all_labels())
        self.root.bind("<Control-o>",          lambda e: self.add_images())
        self.root.bind("<Escape>",             lambda e: self.cancel_label())
        # Zoom
        self.canvas.bind("<Control-MouseWheel>", self.on_zoom)

    # ── File management ────────────────────────────────────────────────────
    def add_images(self):
        paths = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[
                ("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp"),
                ("All Files", "*.*")
            ]
        )
        added = 0
        for p in paths:
            if p not in self.image_list:
                self.image_list.append(p)
                self.labels[p] = []
                self.file_listbox.insert(tk.END, os.path.basename(p))
                added += 1

        self.file_count_label.config(text=f"{len(self.image_list)} files loaded")
        if added:
            self.set_status(f"Added {added} image(s).")
            if self.current_image_index == -1:
                self.load_image(0)

    def on_file_select(self, event):
        selection = self.file_listbox.curselection()
        if selection:
            self.load_image(selection[0])

    def prev_image(self):
        if self.current_image_index > 0:
            self.load_image(self.current_image_index - 1)

    def next_image(self):
        if self.current_image_index < len(self.image_list) - 1:
            self.load_image(self.current_image_index + 1)

    # ── Image loading ──────────────────────────────────────────────────────
    def load_image(self, index):
        if not (0 <= index < len(self.image_list)):
            return

        self.current_image_index = index
        path = self.image_list[index]

        self.file_listbox.selection_clear(0, tk.END)
        self.file_listbox.selection_set(index)
        self.file_listbox.see(index)

        self.original_image = Image.open(path).convert("RGB")
        self.image_name_label.config(text=os.path.basename(path))

        self.fit_image_to_canvas()
        self.refresh_labels_listbox()
        self.set_status(f"Loaded: {os.path.basename(path)} "
                        f"({self.original_image.width}×{self.original_image.height})")

    def fit_image_to_canvas(self):
        if not self.original_image:
            return

        self.canvas.update_idletasks()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()

        iw, ih = self.original_image.size
        scale = min(cw / iw, ch / ih, 1.0)

        self.scale_x = scale
        self.scale_y = scale
        self.zoom_label.config(text=f"Zoom: {int(scale*100)}%")

        disp_w = int(iw * scale)
        disp_h = int(ih * scale)

        resized = self.original_image.resize((disp_w, disp_h), Image.LANCZOS)
        self.current_image = resized
        self.photo_image = ImageTk.PhotoImage(resized)

        self.canvas.config(scrollregion=(0, 0, disp_w, disp_h))
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)

        self.redraw_all_rects()

    def on_zoom(self, event):
        if not self.original_image:
            return
        factor = 1.1 if event.delta > 0 else 0.9
        self.scale_x = max(0.1, min(5.0, self.scale_x * factor))
        self.scale_y = self.scale_x
        self.zoom_label.config(text=f"Zoom: {int(self.scale_x*100)}%")

        iw, ih = self.original_image.size
        disp_w = int(iw * self.scale_x)
        disp_h = int(ih * self.scale_y)

        resized = self.original_image.resize((disp_w, disp_h), Image.LANCZOS)
        self.current_image = resized
        self.photo_image = ImageTk.PhotoImage(resized)

        self.canvas.config(scrollregion=(0, 0, disp_w, disp_h))
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)
        self.redraw_all_rects()

    # ── Drawing ────────────────────────────────────────────────────────────
    def canvas_to_image_coords(self, cx, cy):
        return cx / self.scale_x, cy / self.scale_y

    def image_to_canvas_coords(self, ix, iy):
        return ix * self.scale_x, iy * self.scale_y

    def on_mouse_press(self, event):
        if not self.original_image or self.pending_bbox is not None:
            return
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        self.is_drawing = True
        self.current_rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline=self.colors["rect_default"], width=2, dash=(4, 4)
        )

    def on_mouse_drag(self, event):
        if not self.is_drawing:
            return
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        self.canvas.coords(self.current_rect,
                           self.start_x, self.start_y, cx, cy)

    def on_mouse_release(self, event):
        if not self.is_drawing:
            return
        self.is_drawing = False
        end_x = self.canvas.canvasx(event.x)
        end_y = self.canvas.canvasy(event.y)

        x1, y1 = min(self.start_x, end_x), min(self.start_y, end_y)
        x2, y2 = max(self.start_x, end_x), max(self.start_y, end_y)

        if abs(x2 - x1) < 5 or abs(y2 - y1) < 5:
            self.canvas.delete(self.current_rect)
            self.current_rect = None
            return

        # Convert to image coords
        ix1, iy1 = self.canvas_to_image_coords(x1, y1)
        ix2, iy2 = self.canvas_to_image_coords(x2, y2)

        # Clamp to image bounds
        iw, ih = self.original_image.size
        ix1, iy1 = max(0, ix1), max(0, iy1)
        ix2, iy2 = min(iw, ix2), min(ih, iy2)

        self.pending_bbox = (ix1, iy1, ix2, iy2)
        self.canvas.itemconfig(self.current_rect,
                               outline=self.colors["warning"], dash=())
        self.mode_label.config(text="✏  Enter Label", fg=self.colors["warning"])
        self.label_entry.focus_set()
        self.label_entry.delete(0, tk.END)
        self.set_status("Draw complete. Enter label text and press Confirm or Enter.")

    def confirm_label(self, event=None):
        if self.pending_bbox is None:
            return
        text = self.label_entry.get().strip()
        if not text:
            messagebox.showwarning("Empty Label", "Please enter a label text.")
            self.label_entry.focus_set()
            return

        path = self.image_list[self.current_image_index]
        label_id = self.label_counter
        self.label_counter += 1

        self.labels[path].append({
            "id":   label_id,
            "text": text,
            "bbox": list(self.pending_bbox)
        })

        self.canvas.delete(self.current_rect)
        self.current_rect = None
        self.pending_bbox = None

        self.label_entry.delete(0, tk.END)
        self.mode_label.config(text="✏  Draw Mode", fg=self.colors["accent"])

        self.redraw_all_rects()
        self.refresh_labels_listbox()
        self.set_status(f"Label '{text}' saved.")

    def cancel_label(self, event=None):
        if self.pending_bbox is not None:
            self.pending_bbox = None
            if self.current_rect:
                self.canvas.delete(self.current_rect)
                self.current_rect = None
            self.label_entry.delete(0, tk.END)
            self.mode_label.config(text="✏  Draw Mode", fg=self.colors["accent"])
            self.set_status("Label cancelled.")

    # ── Rect drawing ───────────────────────────────────────────────────────
    def redraw_all_rects(self):
        """Redraw all rectangles and their text tags for the current image."""
        self.canvas.delete("label_rect")
        self.canvas.delete("label_text")

        if self.current_image_index < 0:
            return
        path = self.image_list[self.current_image_index]

        for lbl in self.labels.get(path, []):
            ix1, iy1, ix2, iy2 = lbl["bbox"]
            cx1, cy1 = self.image_to_canvas_coords(ix1, iy1)
            cx2, cy2 = self.image_to_canvas_coords(ix2, iy2)

            color = (self.colors["rect_selected"]
                     if lbl["id"] == self.selected_label_id
                     else self.colors["rect_default"])

            self.canvas.create_rectangle(
                cx1, cy1, cx2, cy2,
                outline=color, width=2,
                tags=("label_rect", f"rect_{lbl['id']}")
            )
            # Semi-transparent label tag
            self.canvas.create_rectangle(
                cx1, cy1 - 18, cx1 + len(lbl["text"]) * 7 + 8, cy1,
                fill=color, outline="", tags=("label_text",)
            )
            self.canvas.create_text(
                cx1 + 4, cy1 - 9,
                text=lbl["text"], anchor="w",
                fill="white", font=("Segoe UI", 8, "bold"),
                tags=("label_text",)
            )

    # ── Labels listbox ─────────────────────────────────────────────────────
    def refresh_labels_listbox(self):
        self.labels_listbox.delete(0, tk.END)
        if self.current_image_index < 0:
            return
        path = self.image_list[self.current_image_index]
        lbls = self.labels.get(path, [])
        for i, lbl in enumerate(lbls):
            bx1, by1, bx2, by2 = [int(v) for v in lbl["bbox"]]
            self.labels_listbox.insert(
                tk.END,
                f"#{i+1}  {lbl['text']}  [{bx1},{by1}→{bx2},{by2}]"
            )
        self.label_count_label.config(text=f"{len(lbls)} label(s)")

    def on_label_select(self, event):
        sel = self.labels_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        path = self.image_list[self.current_image_index]
        lbls = self.labels.get(path, [])
        if idx < len(lbls):
            self.selected_label_id = lbls[idx]["id"]
            self.redraw_all_rects()

    # ── Label actions ──────────────────────────────────────────────────────
    def edit_label(self):
        sel = self.labels_listbox.curselection()
        if not sel:
            messagebox.showinfo("Edit", "Select a label first.")
            return
        idx = sel[0]
        path = self.image_list[self.current_image_index]
        lbl = self.labels[path][idx]

        win = tk.Toplevel(self.root)
        win.title("Edit Label")
        win.configure(bg=self.colors["panel"])
        win.geometry("360x160")
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="Edit label text:",
                 font=("Segoe UI", 10),
                 bg=self.colors["panel"], fg=self.colors["text"]
                 ).pack(pady=(20, 5))

        entry = tk.Entry(win, font=("Segoe UI", 11),
                         bg=self.colors["bg"], fg=self.colors["text"],
                         insertbackground="white", relief=tk.FLAT, bd=8)
        entry.pack(fill=tk.X, padx=20)
        entry.insert(0, lbl["text"])
        entry.select_range(0, tk.END)
        entry.focus_set()

        def apply(e=None):
            new_text = entry.get().strip()
            if new_text:
                lbl["text"] = new_text
                self.redraw_all_rects()
                self.refresh_labels_listbox()
                self.set_status(f"Label updated to '{new_text}'.")
            win.destroy()

        entry.bind("<Return>", apply)
        self.make_button(win, "✔ Save", apply,
                         self.colors["success"]).pack(pady=12)

    def delete_label(self):
        sel = self.labels_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        path = self.image_list[self.current_image_index]
        removed = self.labels[path].pop(idx)
        self.selected_label_id = None
        self.redraw_all_rects()
        self.refresh_labels_listbox()
        self.set_status(f"Deleted label '{removed['text']}'.")

    # ── Export / Save ──────────────────────────────────────────────────────
    def export_current(self):
        """Export cropped images + txt files for the current image."""
        if self.current_image_index < 0:
            messagebox.showinfo("Export", "No image loaded.")
            return
        path = self.image_list[self.current_image_index]
        lbls = self.labels.get(path, [])
        if not lbls:
            messagebox.showinfo("Export", "No labels to export.")
            return

        out_dir = filedialog.askdirectory(title="Select Output Folder")
        if not out_dir:
            return

        self._export_image_labels(path, lbls, out_dir)
        messagebox.showinfo("Done",
                            f"Exported {len(lbls)} label(s) to:\n{out_dir}")
        self.set_status(f"Exported {len(lbls)} label(s).")

    def save_all_labels(self):
        if not self.image_list:
            messagebox.showinfo("Save", "No images loaded.")
            return

        out_dir = filedialog.askdirectory(title="Select Output Folder")
        if not out_dir:
            return

        total = 0
        session = {}

        for path in self.image_list:
            lbls = self.labels.get(path, [])
            if lbls:
                self._export_image_labels(path, lbls, out_dir)
                total += len(lbls)
            session[path] = lbls

        # Save session JSON
        session_path = os.path.join(out_dir, "session.json")
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2, ensure_ascii=False)

        messagebox.showinfo("Saved",
                            f"Exported {total} label(s) from "
                            f"{len(self.image_list)} image(s).\n"
                            f"Session saved to session.json")
        self.set_status(f"All saved → {out_dir}")

    def _export_image_labels(self, image_path, labels, out_dir):
        """
        For each label:
          • crop the region from the original image → save as PNG
          • save the label text → .txt file with the same stem
        Also save a full annotation .txt listing all bboxes.
        """
        img = Image.open(image_path).convert("RGB")
        base = os.path.splitext(os.path.basename(image_path))[0]
        img_out_dir = os.path.join(out_dir, base)
        os.makedirs(img_out_dir, exist_ok=True)

        annotation_lines = []

        for i, lbl in enumerate(labels):
            x1, y1, x2, y2 = [int(v) for v in lbl["bbox"]]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(img.width, x2), min(img.height, y2)

            # Cropped image
            crop = img.crop((x1, y1, x2, y2))
            crop_name = f"{base}_label_{i+1:03d}.png"
            crop.save(os.path.join(img_out_dir, crop_name))

            # Text file (same stem)
            txt_name = f"{base}_label_{i+1:03d}.txt"
            with open(os.path.join(img_out_dir, txt_name),
                      "w", encoding="utf-8") as f:
                f.write(lbl["text"])

            annotation_lines.append(
                f"{crop_name}\t{lbl['text']}\t{x1},{y1},{x2},{y2}"
            )

        # Full annotation file
        ann_path = os.path.join(img_out_dir, f"{base}_annotations.txt")
        with open(ann_path, "w", encoding="utf-8") as f:
            f.write("filename\tlabel\tbbox(x1,y1,x2,y2)\n")
            f.write("\n".join(annotation_lines))

        # Visualised image with all boxes
        vis = img.copy()
        draw = ImageDraw.Draw(vis)
        for lbl in labels:
            x1, y1, x2, y2 = [int(v) for v in lbl["bbox"]]
            draw.rectangle([x1, y1, x2, y2], outline=(124, 58, 237), width=3)
            draw.rectangle([x1, y1 - 18, x1 + len(lbl["text"]) * 8, y1],
                           fill=(124, 58, 237))
            draw.text((x1 + 2, y1 - 17), lbl["text"], fill="white")
        vis.save(os.path.join(img_out_dir, f"{base}_visualized.png"))

    # ── Session ────────────────────────────────────────────────────────────
    def load_session(self):
        path = filedialog.askopenfilename(
            title="Load Session",
            filetypes=[("JSON", "*.json"), ("All", "*.*")]
        )
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            session = json.load(f)

        self.image_list.clear()
        self.labels.clear()
        self.file_listbox.delete(0, tk.END)

        for img_path, lbls in session.items():
            if os.path.isfile(img_path):
                self.image_list.append(img_path)
                self.labels[img_path] = lbls
                self.file_listbox.insert(tk.END, os.path.basename(img_path))

        self.file_count_label.config(text=f"{len(self.image_list)} files loaded")
        if self.image_list:
            self.load_image(0)
        messagebox.showinfo("Session Loaded",
                            f"Loaded {len(self.image_list)} image(s).")

    def clear_all(self):
        if not messagebox.askyesno("Clear All",
                                   "Remove all images and labels?"):
            return
        self.image_list.clear()
        self.labels.clear()
        self.file_listbox.delete(0, tk.END)
        self.labels_listbox.delete(0, tk.END)
        self.canvas.delete("all")
        self.current_image_index = -1
        self.original_image = None
        self.photo_image = None
        self.file_count_label.config(text="0 files loaded")
        self.label_count_label.config(text="0 labels")
        self.image_name_label.config(text="No image selected")
        self.set_status("All cleared.")


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = OCRLabelingTool(root)
    root.mainloop()