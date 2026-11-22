#!/usr/bin/env python3
"""KNULLI Auto Scraper - auto-updating beta, ADB-safe scanning, no scraper backups.

Single detail pane with explicit consent before orphan-data deletion.
Program-created XML backups are cleaned once per connected GUI session.
"""
from __future__ import annotations
from collections import Counter
import os
from pathlib import Path, PurePosixPath
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from app_version import VERSION_TAG
import backend
import backup_cleanup
import orphan_cleanup
import bundle_engine
import core
import legacy_bridge as legacy
import manager
import scrape_options
import setup_engine
import setup_platform_tools
import learned_titles
import user_data

HERE=Path(__file__).resolve().parent
FONT='맑은 고딕'
BG='#141414'; CARD='#202020'; INPUT='#282828'; ALT='#303030'
WHITE=CARD; INK='#f3f3f3'; MUTED='#bbbbbb'; BLUE='#a0a0a0'
ACTIVE='#686868'; CHECKED=CARD; LINE='#414141'; DISABLED='#868686'


def can_rename_rom(item):
    return item.system in manager.SINGLE_FILE.get(PurePosixPath(item.rel).suffix.lower(),set())


def visible_name(item):
    """Consoles show ROM stem, protected archives show KNULLI display title."""
    return item.stem if can_rename_rom(item) else (item.display or item.stem)


class App(tk.Tk):
    def __init__(self, auto_setup=True):
        super().__init__()
        self.title('KNULLI Auto Scraper ' + VERSION_TAG)
        self.geometry('1250x790')
        self.minsize(990,650)
        self.option_add('*Font',(FONT,10))
        self.configure(background=BG)
        self._style()
        self.protocol('WM_DELETE_WINDOW',self.on_close)
        self.q=queue.Queue()
        self.config=backend.load_config()
        self.overrides=backend.load_overrides()
        self.adb=None;self.busy=False
        self._backups_cleaned=False
        self.items={};self.checked=set();self.current=None
        self.preview_file=None;self.preview_img=None;self.preview_request_id=0
        self.pending_check=None
        self.name_var=tk.StringVar()
        self.english_var=tk.StringVar()
        self._english_loading=False
        self._english_pending=None
        self._english_timer=None
        self.english_var.trace_add('write',self._english_changed)
        self.summary_var=tk.StringVar(value='ROM 목록을 불러오는 중…')
        self.status_var=tk.StringVar(value='기기를 연결하고 있습니다…')
        self.detail_metadata={}
        self._build()
        self.after(70,self._pump)
        if auto_setup:self.after(250,self._initial_setup)

    def _style(self):
        """Use explicit ttk styles: native Windows themes ignore many dark colors."""
        style=ttk.Style(self)
        if 'clam' in style.theme_names():style.theme_use('clam')
        self.option_add('*TCombobox*Listbox.background', INPUT)
        self.option_add('*TCombobox*Listbox.foreground', INK)
        self.option_add('*TCombobox*Listbox.selectBackground', ACTIVE)
        self.option_add('*TCombobox*Listbox.selectForeground', INK)
        style.configure('.',font=(FONT,10),background=BG,foreground=INK)
        style.configure('TFrame',background=BG)
        style.configure('Card.TFrame',background=CARD)
        style.configure('TPanedwindow',background=BG)
        style.configure('Sash',sashthickness=8,gripcount=0,background=BG)
        style.configure('TLabel',background=BG,foreground=INK)
        style.configure('Card.TLabel',background=CARD,foreground=INK)
        style.configure('Muted.TLabel',background=CARD,foreground=MUTED)
        style.configure('Title.TLabel',background=BG,foreground=INK,font=(FONT,15,'bold'))
        style.configure('Section.TLabel',background=CARD,foreground=INK,font=(FONT,12,'bold'))
        style.configure('TButton',font=(FONT,10),padding=(11,8),background=ALT,
                        foreground=INK,relief='flat',borderwidth=1,bordercolor=LINE)
        style.map('TButton',background=[('disabled',CARD),('pressed',ACTIVE),('active','#454545')],
                  foreground=[('disabled',DISABLED),('active',INK)],
                  bordercolor=[('focus',BLUE)])
        style.configure('Main.TButton',font=(FONT,10,'bold'),padding=(15,9),
                        background='#555555',foreground='#ffffff',relief='flat',borderwidth=1)
        style.map('Main.TButton',background=[('disabled','#383838'),('pressed','#696969'),('active','#606060')],
                  foreground=[('disabled',DISABLED),('active','#ffffff')])
        style.configure('TEntry',padding=7,fieldbackground=INPUT,foreground=INK,
                        insertcolor=INK,bordercolor=LINE,lightcolor=LINE,darkcolor=LINE)
        style.map('TEntry',fieldbackground=[('disabled',ALT),('readonly',ALT)],
                  foreground=[('disabled',DISABLED),('readonly',INK)],
                  bordercolor=[('focus',BLUE)])
        style.configure('TCombobox',padding=6,fieldbackground=INPUT,background=ALT,foreground=INK,
                        arrowcolor=INK,bordercolor=LINE)
        style.map('TCombobox',fieldbackground=[('readonly',INPUT)],
                  foreground=[('readonly',INK)],background=[('active',CHECKED)])
        style.configure('TCheckbutton',background=CARD,foreground=INK)
        style.map('TCheckbutton',background=[('active',CARD)],foreground=[('disabled',DISABLED)])
        style.configure('TRadiobutton',background=CARD,foreground=INK)
        style.map('TRadiobutton',background=[('active',CARD)],foreground=[('disabled',DISABLED)])
        style.configure('TLabelframe',background=CARD,bordercolor=LINE,relief='solid')
        style.configure('TLabelframe.Label',background=CARD,foreground=INK,font=(FONT,10,'bold'))
        style.configure('TNotebook',background=BG,borderwidth=0)
        style.configure('TNotebook.Tab',background=ALT,foreground=MUTED,padding=(15,8),borderwidth=0)
        style.map('TNotebook.Tab',background=[('selected',CARD),('active',CHECKED)],
                  foreground=[('selected',INK),('active',INK)])
        style.configure('Vertical.TScrollbar',background=LINE,troughcolor=BG,
                        arrowcolor=MUTED,bordercolor=BG,relief='flat',gripcount=0,
                        width=13)
        style.map('Vertical.TScrollbar',background=[('active',ACTIVE),('pressed',BLUE)])
        style.configure('Horizontal.TProgressbar',background=BLUE,troughcolor=ALT,
                        borderwidth=0,lightcolor=BLUE,darkcolor=BLUE)
        style.configure('Treeview',font=(FONT,10),rowheight=35,background=CARD,
                        foreground=INK,fieldbackground=CARD,borderwidth=0)
        style.configure('Treeview.Heading',font=(FONT,10,'bold'),padding=(8,10),
                        background=ALT,foreground=INK,relief='flat')
        style.map('Treeview.Heading',background=[('active',CHECKED)])
        # Keep the active line highlighted even when focus moves to an editor.
        style.map('Treeview',background=[('selected','!focus',ACTIVE),('selected',ACTIVE)],
                  foreground=[('selected','!focus','#ffffff'),('selected','#ffffff')])

    def _build(self):
        header=ttk.Frame(self,padding=(16,13,16,9));header.pack(fill='x')
        ttk.Label(header,text='KNULLI Auto Scraper',style='Title.TLabel').pack(side='left')
        self.btn_settings=ttk.Button(header,text='스크래핑 설정',command=self.settings)
        self.btn_settings.pack(side='right')

        toolbar=ttk.Frame(self,padding=(16,0,16,12));toolbar.pack(fill='x')
        self.btn_all=ttk.Button(toolbar,text='전체 선택',command=lambda:self.bulk('all'))
        self.btn_all.pack(side='left',padx=(0,6))
        self.btn_missing=ttk.Button(toolbar,text='데이터 없는 게임 선택',command=lambda:self.bulk('missing'))
        self.btn_missing.pack(side='left',padx=(0,6))
        self.btn_failed=ttk.Button(toolbar,text='실패 항목 선택',command=lambda:self.bulk('failed'))
        self.btn_failed.pack(side='left',padx=(0,6))
        self.btn_go=ttk.Button(toolbar,text='작업 시작',style='Main.TButton',command=self.scrape)
        self.btn_go.pack(side='right')

        body=ttk.PanedWindow(self,orient='horizontal');body.pack(fill='both',expand=True,padx=16,pady=(0,8))
        left=ttk.Frame(body,style='Card.TFrame',padding=10)
        right=ttk.Frame(body,style='Card.TFrame',padding=12)
        body.add(left,weight=6);body.add(right,weight=5)

        list_head=ttk.Frame(left,style='Card.TFrame');list_head.pack(fill='x',pady=(2,10))
        ttk.Label(list_head,text='ROM 목록',style='Section.TLabel').pack(side='left')
        ttk.Label(list_head,textvariable=self.summary_var,style='Muted.TLabel').pack(side='right')
        list_body=ttk.Frame(left,style='Card.TFrame');list_body.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(list_body,columns=('check','system','name','status'),show='headings',selectmode='browse')
        for key,title,width,anchor in [('check','',47,'center'),('system','기종',84,'center'),
                                       ('name','게임명',340,'w'),('status','상태',124,'center')]:
            self.tree.heading(key,text=title,anchor=anchor)
            self.tree.column(key,width=(60 if key=='check' else width),anchor=anchor,stretch=(key=='name'),minwidth=35)
        self.tree.tag_configure('active_row',background=ACTIVE,foreground='#ffffff',font=(FONT,10,'bold'))
        self.tree.tag_configure('checked_row',background=CARD,foreground=INK)
        self.tree.tag_configure('error_row',background=CARD,foreground='#f5aaaa')
        self.tree.tag_configure('no_data',background=CARD,foreground=INK)
        sb=ttk.Scrollbar(list_body,orient='vertical',command=self.tree.yview)
        sb.pack(side='right',fill='y')
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side='left',fill='both',expand=True)
        self.tree.bind('<Button-1>',self.click_row)
        self.tree.bind('<Double-1>',self.double_click_row)
        self.tree.bind('<space>',self.space_toggle)
        self.tree.bind('<<TreeviewSelect>>',self.select_row)

        # Only one game-detail view; scrollable for smaller screens.
        ttk.Label(right,text='게임 정보',style='Section.TLabel').pack(anchor='w',pady=(1,9))
        holder=ttk.Frame(right,style='Card.TFrame');holder.pack(fill='both',expand=True)
        canvas=tk.Canvas(holder,highlightthickness=0,background=CARD,yscrollincrement=18)
        self.detail_canvas=canvas
        scrollbar=ttk.Scrollbar(holder,orient='vertical',command=canvas.yview)
        scrollbar.pack(side='right',fill='y')
        canvas.pack(side='left',fill='both',expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        self.detail=ttk.Frame(canvas,style='Card.TFrame',padding=(2,0,10,10))
        win=canvas.create_window((0,0),window=self.detail,anchor='nw')
        self.detail.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda e:canvas.itemconfigure(win,width=e.width))
        # Mouse-wheel bindings for *all* children are installed after the detail UI
        # is created; binding only the canvas fails while hovering over labels/entries.

        ttk.Label(self.detail,text='이름',style='Muted.TLabel').pack(anchor='w',pady=(4,5))
        name_row=ttk.Frame(self.detail,style='Card.TFrame');name_row.pack(fill='x')
        self.name_entry=ttk.Entry(name_row,textvariable=self.name_var)
        self.name_entry.pack(side='left',fill='x',expand=True)
        self.extension=ttk.Label(name_row,text='',style='Muted.TLabel')
        self.extension.pack(side='left',padx=(8,4))
        self.btn_name=ttk.Button(name_row,text='저장',command=self.save_name)
        self.btn_name.pack(side='right',padx=(6,0))
        self.name_entry.bind('<Return>',lambda event:self.save_name())

        ttk.Label(self.detail,text='영어 게임명',style='Muted.TLabel').pack(anchor='w',pady=(11,4))
        english_row=ttk.Frame(self.detail,style='Card.TFrame');english_row.pack(fill='x')
        self.english_entry=ttk.Entry(english_row,textvariable=self.english_var,width=26)
        self.english_entry.pack(side='left',anchor='w')
        self.english_entry.bind('<Return>',self._english_commit_event)
        self.english_entry.bind('<FocusOut>',self._english_commit_event)

        self.preview_box=ttk.Frame(self.detail,style='Card.TFrame')
        self.preview_box.pack(fill='x',pady=(11,3))
        self.preview_box.configure(height=194)
        self.preview_box.pack_propagate(False)
        self.image_label=ttk.Label(self.preview_box,text='이미지가 없습니다',style='Muted.TLabel',anchor='center')
        self.image_label.pack(fill='both',expand=True)

        ttk.Label(self.detail,text='게임 정보',style='Section.TLabel').pack(anchor='w',pady=(7,5))
        self.meta_frame=ttk.Frame(self.detail,style='Card.TFrame');self.meta_frame.pack(fill='x')
        for i,(key,label) in enumerate([('genre','장르'),('rating','평점'),('releasedate','출시일'),
                                        ('developer','개발사'),('publisher','배급사'),('players','플레이어')]):
            row=i//2; col=(i%2)*2
            ttk.Label(self.meta_frame,text=label,style='Muted.TLabel',width=7).grid(
                row=row,column=col,sticky='nw',pady=4,padx=(0,5))
            val=ttk.Label(self.meta_frame,text='—',style='Card.TLabel',wraplength=130,justify='left')
            val.grid(row=row,column=col+1,sticky='ew',pady=4,padx=(0,8))
            self.detail_metadata[key]=val
        self.meta_frame.columnconfigure(1,weight=1)
        self.meta_frame.columnconfigure(3,weight=1)
        ttk.Label(self.detail,text='설명',style='Muted.TLabel').pack(anchor='w',pady=(10,5))
        self.description=tk.Text(self.detail,height=5,wrap='word',font=(FONT,10),
                                 relief='solid',borderwidth=1,background=INPUT,foreground=INK,insertbackground=INK,
                                 selectbackground=ACTIVE,selectforeground='#ffffff',
                                 highlightthickness=1,highlightbackground=LINE,highlightcolor=BLUE,
                                 padx=10,pady=9,undo=True)
        self.description.pack(fill='x')
        self.btn_description=ttk.Button(self.detail,text='설명 저장',command=self.save_description)
        self.btn_description.pack(anchor='e',pady=(8,3))

        footer=ttk.Frame(self,padding=(16,0,16,13));footer.pack(fill='x')
        self.progress=ttk.Progressbar(footer,maximum=1,mode='determinate')
        self.progress.pack(fill='x')
        ttk.Label(footer,textvariable=self.status_var,foreground=MUTED,wraplength=1200).pack(anchor='w',pady=(5,0))
        self.action_buttons=[self.btn_all,self.btn_missing,self.btn_failed,self.btn_settings,self.btn_go]
        self.edit_buttons=[self.btn_name,self.btn_description]
        self._set_editable(False)
        self._bind_detail_wheel(canvas)
        self._bind_detail_wheel(scrollbar)
        self._bind_detail_wheel(self.detail)

    def _bind_detail_wheel(self,widget):
        # Bind children before default Text/Entry class handlers.
        widget.bind('<MouseWheel>',self._on_detail_wheel,add='+')
        widget.bind('<Button-4>',self._on_detail_wheel,add='+')
        widget.bind('<Button-5>',self._on_detail_wheel,add='+')
        for child in widget.winfo_children():
            self._bind_detail_wheel(child)

    def _on_detail_wheel(self,event):
        # Scroll the whole detail panel, not individual child widgets.
        if getattr(event,'num',None)==4:
            steps=-3
        elif getattr(event,'num',None)==5:
            steps=3
        else:
            delta=getattr(event,'delta',0)
            if not delta:return
            # Support both regular wheel (120) and fractional touchpad deltas.
            steps=(-1 if delta>0 else 1)*3*max(1,round(abs(delta)/120))
        self.detail_canvas.yview_scroll(steps,'units')
        return 'break'

    def _thread(self,fn): threading.Thread(target=fn,daemon=True).start()

    def _set_editable(self,enable):
        item=self.active()
        normal=bool(enable and item and not self.busy)
        for widget in self.edit_buttons:widget.configure(state='normal' if normal else 'disabled')
        self.name_entry.configure(state='normal' if normal else 'disabled')
        self.english_entry.configure(state='normal' if normal else 'disabled')
        self.description.configure(state='normal' if normal else 'disabled')

    def _busy(self,value):
        self.busy=value
        for widget in self.action_buttons:widget.configure(state='disabled' if value else 'normal')
        self._set_editable(not value)

    def _initial_setup(self):
        self._busy(True)
        self.status_var.set('필요한 도구 확인 중…')
        def job():
            adb_error=None;engine_error=None
            try:
                adb=setup_platform_tools.existing_adb(self.config)
                if not adb:adb=setup_platform_tools.setup(lambda s:self.q.put(('status',s)))
            except Exception as exc:adb_error=str(exc)
            # Skyscraper is intentionally lazy-installed only when the user
            # selects a console ROM for scraping. PortMaster-only libraries
            # must not require Skyscraper or an installer download.
            self.q.put(('setup-finished',(adb_error,engine_error)))
        self._thread(job)

    def scan(self):
        if self.busy:return
        self._busy(True);self.status_var.set('ROM 목록을 확인하는 중…')
        def job():
            try:
                adb=core.Adb(os.environ.get('ADB_PATH') or self.config.get('adb_path'))
                serial=adb.connect()
                backup_report=None;backup_error=''
                if not self._backups_cleaned:
                    try:
                        backup_report=backup_cleanup.cleanup(
                            adb,self.config,backend.HERE/'work')
                    except Exception as exc:
                        backup_error=str(exc)[:180]
                rows=backend.catalogue(adb,self.config)
                # Synchronize Korean filename-derived titles directly in KNULLI XML.
                # This is not a scrape and never renames a ROM or touches other fields.
                sync_count=0;sync_error=''
                try:
                    sync_count=backend.sync_korean_names(adb,self.config,rows)
                except Exception as exc:
                    sync_error=str(exc)[:160]
                cleanup_plan=None;cleanup_error=''
                try:
                    cleanup_plan=orphan_cleanup.inspect(adb,self.config)
                except Exception as exc:
                    cleanup_error=str(exc)[:180]
                self.q.put(('scanned',(adb,serial,rows,sync_count,sync_error,
                                       cleanup_plan,cleanup_error,
                                       backup_report,backup_error)))
            except Exception as exc:self.q.put(('fatal','ROM 조회 실패: '+str(exc)))
        self._thread(job)

    def _offer_cleanup(self,plan):
        """Confirm destructive cleanup explicitly; discovery itself is read-only."""
        if self.busy or not plan.game_count:
            return
        examples='\n'.join('• '+name for name in plan.examples(5))
        if plan.game_count>5:
            examples+='\n• 외 '+str(plan.game_count-5)+'개'
        question=(f'기기에 ROM 파일이 없는 게임 항목 {plan.game_count}개를 찾았습니다.\n\n'
                  f'{examples}\n\n'
                  f'gamelist.xml에서 해당 항목을 제거하고, 다른 게임이 사용하지 않는 '
                  f'관련 이미지·영상·매뉴얼 최대 {plan.media_count}개를 정리합니다.\n'
                  'XML 백업을 만들지 않습니다. 관련 미디어 삭제는 되돌리기 어려울 수 있습니다.\n\n지금 정리하시겠습니까?')
        if not messagebox.askyesno('삭제된 게임 자료 정리',question,
                                   icon='warning',default='no'):
            self.status_var.set('삭제된 게임 자료 정리를 건너뛰었습니다.')
            return
        self._busy(True)
        self.status_var.set('삭제된 게임 관련 자료를 정리하는 중…')
        def job():
            try:
                result=orphan_cleanup.apply(self.adb,plan,backend.HERE/'work')
                self.q.put(('cleanup-done',result))
            except Exception as exc:
                self.q.put(('cleanup-failed',str(exc)))
        self._thread(job)

    def _glyph(self,rid):
        # Visible focus marker even if a Windows ttk theme overrides selection color.
        return ('▸ ' if rid==self.current else '  ')+('☑' if rid in self.checked else '☐')

    @staticmethod
    def _status_text(item):
        # Status is always readable in its own final column (not solely color-coded).
        label=item.status or ('데이터 있음' if item.has_data else '데이터 없음')
        mapping={'적용 완료':'✓ 작업 성공', 'applied':'✓ 작업 성공',
                 '데이터 있음':'● 데이터 있음', '변경 없음':'● 데이터 있음',
                 '데이터 없음':'○ 데이터 없음', '자원 경로만 있음':'○ 데이터 없음',
                 '검색 실패':'✕ 검색 실패', '오류':'✕ 작업 실패', 'XML 오류':'✕ XML 오류',
                 '진행 중':'… 작업 중', '작업 중':'… 작업 중',
                 '지원 안 함':'— 지원 안 함', '용량 초과':'— 용량 초과'}
        return mapping.get(label,label)

    def _row_tag(self,rid):
        item=self.items.get(rid)
        if not item:return ''
        if rid==self.current:return 'active_row'
        if rid in self.checked:return 'checked_row'
        if item.status in ('검색 실패','오류','XML 오류'):return 'error_row'
        if not item.has_data:return 'no_data'
        return ''

    def _restyle_row(self,rid):
        if rid and self.tree.exists(rid):
            tag=self._row_tag(rid)
            self.tree.item(rid,tags=(tag,) if tag else ())

    def _update_summary(self):
        self.summary_var.set(f'{len(self.items)}개 · 선택 {len(self.checked)}개')
        for rid in self.items:
            if self.tree.exists(rid):
                self.tree.set(rid,'check',self._glyph(rid))
                self.tree.set(rid,'status',self._status_text(self.items[rid]))
                self._restyle_row(rid)

    def _insert_item(self,item):
        values=(self._glyph(item.rel),item.system.upper() if item.system not in ('neogeo','megadrive','gamegear','ports','atomiswave')
                else {'neogeo':'Neo Geo','megadrive':'Mega Drive','gamegear':'Game Gear','ports':'PortMaster','atomiswave':'Atomiswave'}[item.system],
                visible_name(item),self._status_text(item))
        self.tree.insert('','end',iid=item.rel,values=values)

    def _paint(self,rows,focus=None):
        self.items={r.rel:r for r in rows}
        self.checked.intersection_update(self.items)
        for rid in self.tree.get_children():self.tree.delete(rid)
        for row in sorted(rows,key=lambda r:(r.system,visible_name(r).casefold())):
            self._insert_item(row)
        self._update_summary()
        if rows:
            selected=focus if focus in self.items else self.tree.get_children()[0]
            self.tree.selection_set(selected);self.tree.focus(selected);self.tree.see(selected)
            self.select_row()
        else:
            # Deleting the final ROM must not leave stale, editable game data.
            self.current=None
            self.name_var.set('')
            self.extension.configure(text='')
            self._english_loading=True
            try:self.english_var.set('')
            finally:self._english_loading=False
            self.preview_request_id+=1
            self.preview_img=None
            self.image_label.configure(image='',text='게임이 없습니다')
            for widget in self.detail_metadata.values():widget.configure(text='—')
            self.description.configure(state='normal')
            self.description.delete('1.0','end')
            self._set_editable(False)

    def _toggle(self,rid):
        if self.busy or rid not in self.items:return
        if rid in self.checked:self.checked.remove(rid)
        else:self.checked.add(rid)
        self._update_summary()

    def click_row(self,event):
        # A delayed single-click on the check cell avoids double-click toggling twice.
        rid=self.tree.identify_row(event.y)
        if not rid or self.tree.identify_region(event.x,event.y) not in ('cell','tree'):return
        if self.tree.identify_column(event.x)=='#1':
            self.tree.focus(rid);self.tree.selection_set(rid)
            if self.pending_check:
                try:self.after_cancel(self.pending_check)
                except ValueError:pass
            self.pending_check=self.after(250,lambda r=rid:self._on_check_timeout(r))
            return 'break'

    def _on_check_timeout(self,rid):
        self.pending_check=None
        self._toggle(rid)

    def double_click_row(self,event):
        if self.pending_check:
            try:self.after_cancel(self.pending_check)
            except ValueError:pass
            self.pending_check=None
        rid=self.tree.identify_row(event.y)
        if rid:
            self.tree.focus(rid);self.tree.selection_set(rid)
            self._toggle(rid)
            return 'break'

    def space_toggle(self,event):
        rid=self.tree.focus() or next(iter(self.tree.selection()),None)
        if rid:self._toggle(rid)
        return 'break'

    def bulk(self,mode):
        if self.busy:return
        if mode=='all':self.checked=set(self.items)
        elif mode=='missing':self.checked={k for k,v in self.items.items() if not v.has_data}
        elif mode=='failed':self.checked={k for k,v in self.items.items() if v.status in ('검색 실패','오류')}
        self._update_summary()

    def active(self):
        selected=self.tree.selection()
        return self.items.get(selected[0]) if selected else None

    def select_row(self,event=None):
        self._flush_english_pending()
        item=self.active()
        if item is None:return
        prior=self.current
        self.current=item.rel
        self._restyle_row(prior)
        self._restyle_row(item.rel)
        if prior!=item.rel:
            for rid in (prior,item.rel):
                if rid and self.tree.exists(rid):
                    self.tree.set(rid,'check',self._glyph(rid))
        if prior!=item.rel:
            self.detail_canvas.yview_moveto(0)
        self.name_var.set(visible_name(item))
        self.extension.configure(text=PurePosixPath(item.rel).suffix if can_rename_rom(item) else '')
        db=user_data.load_titles()
        english=(self.overrides.get(item.rel) or learned_titles.lookup(db,item.system,item.stem) or '')
        self._english_loading=True
        try:self.english_var.set(english)
        finally:self._english_loading=False
        for key,widget in self.detail_metadata.items():
            widget.configure(text=item.metadata.get(key) or '—')
        self.description.configure(state='normal')
        self.description.delete('1.0','end')
        self.description.insert('1.0',item.metadata.get('desc',''))
        self._set_editable(not self.busy)
        self.request_preview()

    def request_preview(self):
        item=self.active()
        self.preview_file=None;self.preview_img=None
        self.preview_request_id+=1
        token=self.preview_request_id
        self.image_label.configure(image='',text='이미지 확인 중…' if item else '게임을 선택하세요')
        if item is None:return
        if 'image' not in item.resource_paths:
            self.image_label.configure(image='',text='이미지가 없습니다')
            return
        def job():
            try:
                out=backend.fetch_resource(self.adb,item,'image')
                self.q.put(('preview',(token,item.rel,out,None)))
            except Exception as exc:self.q.put(('preview',(token,item.rel,None,str(exc))))
        self._thread(job)

    def _draw_preview(self,path,error):
        if error or not path:
            self.image_label.configure(image='',text='미리보기를 불러올 수 없습니다')
            return
        self.preview_file=path
        if path.suffix.lower() not in ('.png','.jpg','.jpeg','.gif','.webp'):
            self.image_label.configure(image='',text='이미지 형식이 아닙니다')
            return
        try:
            from PIL import Image, ImageTk
            with Image.open(path) as im:
                im.thumbnail((445,242))
                photo=ImageTk.PhotoImage(im.copy())
        except ImportError:
            if path.suffix.lower() not in ('.png','.gif'):
                self.image_label.configure(text='JPG/WEBP 미리보기에는 Pillow가 필요합니다',image='')
                return
            photo=tk.PhotoImage(file=str(path))
            factor=max(1,int(max(photo.width()/440,photo.height()/240)+0.999))
            if factor>1:photo=photo.subsample(factor,factor)
        except Exception:
            self.image_label.configure(image='',text='이미지를 표시하지 못했습니다')
            return
        self.preview_img=photo
        self.image_label.configure(image=photo,text='')

    def _english_changed(self,*_):
        """Queue an edit by ROM identity so selection changes cannot mis-save it."""
        if self._english_loading or self.busy:
            return
        item=self.active()
        if not item:
            return
        self._english_pending=(item.rel,self.english_var.get())
        self._cancel_english_timer()
        self._english_timer=self.after(850,self._flush_english_pending)

    def _cancel_english_timer(self):
        if self._english_timer is not None:
            try:self.after_cancel(self._english_timer)
            except (ValueError,tk.TclError):pass
            self._english_timer=None

    def _english_commit_event(self,event=None):
        self._flush_english_pending()
        if event and getattr(event,'keysym','')=='Return':
            return 'break'

    def _flush_english_pending(self):
        self._cancel_english_timer()
        pending=self._english_pending
        if pending is None:
            return True
        rid,raw=pending
        value=raw.strip()
        if len(value)>150 or '\n' in value or '\r' in value:
            self.status_var.set('영어 게임명은 150자 이하 한 줄로 입력하세요.')
            return False
        try:
            new=dict(self.overrides)
            if value:new[rid]=value
            else:new.pop(rid,None)
            if new!=self.overrides:
                backend.save_overrides(new)
                self.overrides=new
                self.status_var.set('영어 게임명 자동 저장 완료')
            self._english_pending=None
            return True
        except Exception as exc:
            self.status_var.set('영어 게임명 저장 실패: '+str(exc)[:120])
            return False

    def save_search(self):
        """Backward-compatible explicit commit for scrape and older automation."""
        item=self.active()
        if not item or self.busy:
            return
        self._english_pending=(item.rel,self.english_var.get())
        self._flush_english_pending()

    def save_name(self):
        self._flush_english_pending()
        if self.busy:return
        item=self.active()
        if item is None:return
        new=self.name_var.get().strip()
        if not new or len(new)>200:
            messagebox.showwarning('이름','올바른 게임명을 입력하세요.');return
        if can_rename_rom(item):
            proposal=manager.complete_filename(PurePosixPath(item.rel).name,new)
            if new==item.stem:
                if item.display!=new:
                    self._busy(True)
                    def sync_name():
                        try:
                            changed=manager.update_metadata(self.adb,item,{'name':new},work=HERE/'work')
                            self.q.put(('saved',(item.rel,changed)))
                        except Exception as exc:self.q.put(('fatal','표시명 동기화 실패: '+str(exc)))
                    self._thread(sync_name)
                return
            try:manager.validate_name(PurePosixPath(item.rel).name,proposal,item.system)
            except ValueError as exc:messagebox.showwarning('파일명 변경',str(exc));return
            if not messagebox.askyesno('파일명 변경',f'{item.stem} → {new}\n\nROM 파일과 연결된 XML 및 자원 경로를 변경할까요?'):
                return
            self._busy(True)
            def job():
                try:
                    plan=manager.rename_rom(self.adb,item,proposal,work=HERE/'work')
                    old=item.rel;new_rel=plan['new_rel'][2:]
                    if old in self.overrides:
                        self.overrides[new_rel]=self.overrides.pop(old)
                        backend.save_overrides(self.overrides)
                    names=user_data.load_titles()
                    learned_titles.migrate(names,item.system,item.stem,Path(proposal).stem)
                    user_data.save_titles(names)
                    self.q.put(('renamed',(old,new_rel)))
                except Exception as exc:self.q.put(('fatal','파일명 변경 실패: '+str(exc)))
            self._thread(job)
        else:
            if new==item.display:return
            if not messagebox.askyesno('표시명 저장',f'게임 목록에 표시할 이름을 「{new}」(으)로 변경할까요?\nROM 파일은 변경하지 않습니다.'):
                return
            self._busy(True)
            def job():
                try:
                    changed=manager.update_metadata(self.adb,item,{'name':new},work=HERE/'work')
                    self.q.put(('saved',(item.rel,changed)))
                except Exception as exc:self.q.put(('fatal','표시명 저장 실패: '+str(exc)))
            self._thread(job)

    def save_description(self):
        if self.busy:return
        item=self.active()
        if not item:return
        value=self.description.get('1.0','end-1c').strip()
        if value==(item.metadata.get('desc') or '').strip():return
        if not messagebox.askyesno('설명 저장','현재 게임의 설명을 저장할까요?\nXML 백업은 생성하지 않습니다.'):
            return
        self._busy(True)
        def job():
            try:
                result=manager.update_metadata(self.adb,item,{'desc':value},work=HERE/'work')
                self.q.put(('saved',(item.rel,result)))
            except Exception as exc:self.q.put(('fatal','설명 저장 실패: '+str(exc)))
        self._thread(job)

    def settings(self):
        self._flush_english_pending()
        if self.busy:return
        dlg=tk.Toplevel(self);dlg.title('스크래핑 설정');dlg.transient(self)
        dlg.configure(background=BG)
        dlg.geometry('700x665');dlg.minsize(650,585);dlg.grab_set()
        wrap=ttk.Frame(dlg,padding=14);wrap.pack(fill='both',expand=True)
        # Pack the footer first so Save/Cancel never get pushed off a short screen.
        foot=ttk.Frame(wrap);foot.pack(side='bottom',fill='x',pady=(10,0))
        notebook=ttk.Notebook(wrap);notebook.pack(side='top',fill='both',expand=True)
        scraper_tab=ttk.Frame(notebook,style='Card.TFrame')
        account=ttk.Frame(notebook,style='Card.TFrame',padding=9)
        notebook.add(scraper_tab,text='스크래핑 항목')
        notebook.add(account,text='ScreenScraper 계정')
        scraper_canvas=tk.Canvas(scraper_tab,highlightthickness=0,background=CARD,yscrollincrement=18)
        scraper_scrollbar=ttk.Scrollbar(scraper_tab,orient='vertical',command=scraper_canvas.yview)
        scraper_scrollbar.pack(side='right',fill='y')
        scraper_canvas.pack(side='left',fill='both',expand=True)
        scraper_canvas.configure(yscrollcommand=scraper_scrollbar.set)
        scraper=ttk.Frame(scraper_canvas,style='Card.TFrame',padding=9)
        scraper_window=scraper_canvas.create_window((0,0),window=scraper,anchor='nw')
        scraper.bind('<Configure>',lambda event:scraper_canvas.configure(scrollregion=scraper_canvas.bbox('all')))
        scraper_canvas.bind('<Configure>',lambda event:scraper_canvas.itemconfigure(scraper_window,width=event.width))
        prefs=scrape_options.options(self.config)
        selectors={};toggles={}
        def selector(frame,title,choices,key):
            box=ttk.LabelFrame(frame,text=title,padding=7);box.pack(fill='x',pady=(0,7))
            var=tk.StringVar(value=prefs[key]);selectors[key]=var
            for i,(label,val,supported) in enumerate(choices):
                ttk.Radiobutton(box,text=label,value=val,variable=var,
                                state='normal' if supported else 'disabled').grid(row=i//4,column=i%4,sticky='w',padx=(0,11),pady=3)
        selector(scraper,'이미지 소스',scrape_options.IMAGE_OPTIONS,'image_source')
        selector(scraper,'박스 소스',scrape_options.BOX_OPTIONS,'box_source')
        selector(scraper,'로고 소스',scrape_options.LOGO_OPTIONS,'logo_source')
        region_names={k:v for k,v in scrape_options.REGION_OPTIONS}
        region=ttk.Frame(scraper);region.pack(fill='x',pady=(3,9))
        ttk.Label(region,text='우선 지역').pack(side='left')
        region_var=tk.StringVar(value=next((name for name,v in region_names.items()
                                            if v==prefs['preferred_region']),'자동'))
        ttk.Combobox(region,textvariable=region_var,state='readonly',width=16,
                     values=list(region_names)).pack(side='left',padx=12)
        toggles_box=ttk.LabelFrame(scraper,text='기타 항목',padding=9)
        toggles_box.pack(fill='both',expand=True)
        flags=[(k,label,sup) for k,label,sup in scrape_options.KNULLI_FLAGS if k!='overwrite_names']
        flags += [(k,label,True) for k,label in scrape_options.EXTRA]
        for index,(key,label,supported) in enumerate(flags):
            v=tk.BooleanVar(value=bool(prefs[key]) if supported else False);toggles[key]=v
            ttk.Checkbutton(toggles_box,text=label,variable=v,
                            state='normal' if supported else 'disabled').grid(
                                row=index//3,column=index%3,padx=(0,10),pady=5,sticky='w')
        credentials=self.config.get('screenscraper_account',{})
        username=tk.StringVar(value=credentials.get('user',''))
        password=tk.StringVar(value=credentials.get('password',''))
        ttk.Label(account,text='사용자 ID').grid(row=0,column=0,sticky='w',pady=9)
        ttk.Entry(account,textvariable=username,width=45).grid(row=0,column=1,sticky='ew',padx=10)
        ttk.Label(account,text='비밀번호').grid(row=1,column=0,sticky='w',pady=9)
        ttk.Entry(account,textvariable=password,show='●',width=45).grid(row=1,column=1,sticky='ew',padx=10)
        ttk.Label(account,text='계정은 Windows 자격 증명 관리자에 저장됩니다.',foreground=MUTED,
                  wraplength=525).grid(row=2,column=0,columnspan=2,sticky='w',pady=(12,0))
        ttk.Label(account,text='영어 제목 사전: 문서\\KNULLI Auto Scraper Data\\title_map.csv',
                  foreground=MUTED,wraplength=525).grid(row=3,column=0,columnspan=2,sticky='w',pady=7)
        account.columnconfigure(1,weight=1)
        # Mirror the game-info wheel behavior inside the scraper settings tab.
        def settings_wheel(event):
            if getattr(event,'num',None)==4:steps=-3
            elif getattr(event,'num',None)==5:steps=3
            else:
                delta=getattr(event,'delta',0)
                if not delta:return
                steps=(-1 if delta>0 else 1)*3*max(1,round(abs(delta)/120))
            scraper_canvas.yview_scroll(steps,'units')
            return 'break'
        def bind_settings_wheel(widget):
            for sequence in ('<MouseWheel>','<Button-4>','<Button-5>'):
                widget.bind(sequence,settings_wheel,add='+')
            for child in widget.winfo_children():bind_settings_wheel(child)
        bind_settings_wheel(scraper_canvas)
        bind_settings_wheel(scraper)
        def save():
            new=dict(prefs)
            for key,v in selectors.items():new[key]=v.get()
            new['preferred_region']=region_names[region_var.get()]
            for key,v in toggles.items():new[key]=bool(v.get())
            new['overwrite_names']=False
            updated=dict(self.config)
            updated['knulli_scraper']=new
            updated['screenscraper_account']={'user':username.get().strip(),'password':password.get()}
            try:backend.save_config(updated)
            except Exception as exc:
                messagebox.showerror('설정 저장 실패',str(exc),parent=dlg);return
            self.config=updated
            self.status_var.set('스크래핑 설정 저장 완료')
            dlg.destroy()
        ttk.Button(foot,text='저장',command=save).pack(side='right')
        ttk.Button(foot,text='취소',command=dlg.destroy).pack(side='right',padx=6)
        dlg.wait_window()

    def scrape(self):
        if self.busy:return
        # Commit current search name even if Enter/Save wasn't clicked.
        self.save_search()
        chosen=[self.items[r] for r in self.tree.get_children() if r in self.checked]
        if not chosen:
            messagebox.showinfo('선택 없음','작업할 게임을 선택하세요.');return
        try:
            if any(item.system!='ports' for item in chosen):
                legacy.find_engine(self.config.get('skyscraper_path',''))
        except RuntimeError:
            self._busy(True);self.status_var.set('Skyscraper 설치 중…')
            def job():
                try:
                    setup_engine.setup(lambda s:self.q.put(('status',s)))
                    self.q.put(('engine-installed',chosen))
                except Exception as exc:self.q.put(('fatal','Skyscraper 설치 실패: '+str(exc)))
            self._thread(job);return
        self._start_scrape(chosen)

    def _start_scrape(self,chosen):
        if not messagebox.askyesno('작업 시작',f'{len(chosen)}개 게임을 스크래핑하고 기기에 적용할까요?\nXML 백업은 생성하지 않습니다.'):
            self._busy(False);return
        self._busy(True)
        self.progress.configure(value=0,maximum=len(chosen))
        self.status_var.set(f'작업 시작 · {len(chosen)}개')
        def job():
            def progress(i,total,item,status,note):
                self.q.put(('work-step',(i,total,item.rel,status,note)))
                if status!='진행 중':
                    try:
                        refreshed=(backend.refresh_item(self.adb,self.config,item)
                                   if status in ('applied','unchanged') else item)
                        refreshed.details=note
                        refreshed.status={'applied':'적용 완료','unchanged':'변경 없음',
                                          'unmatched':'검색 실패','error':'오류',
                                          'unsupported_platform':'지원 안 함',
                                          'rom_too_large':'용량 초과'}.get(status,status)
                        self.q.put(('work-item',refreshed))
                    except Exception as exc:
                        self.q.put(('status',f'{item.rel} 완료 · 상세 갱신 지연: {str(exc)[:80]}'))
            try:
                report=bundle_engine.process_selected(self.adb,self.config,chosen,dict(self.overrides),progress)
                self.q.put(('worked',report))
            except Exception as exc:self.q.put(('fatal','스크래핑 작업 실패: '+str(exc)))
        self._thread(job)

    def _update_one(self,item):
        self.items[item.rel]=item
        if self.tree.exists(item.rel):
            self.tree.set(item.rel,'name',visible_name(item))
            self.tree.set(item.rel,'status',self._status_text(item))
            self._restyle_row(item.rel)
        if self.current==item.rel:self.select_row()

    def _pump(self):
        try:
            for _ in range(100):
                msg,value=self.q.get_nowait()
                if msg=='status':self.status_var.set(value)
                elif msg=='setup-finished':
                    adb_error,engine_error=value
                    self._busy(False)
                    if adb_error:
                        self.status_var.set('ADB 준비 실패: '+adb_error)
                        messagebox.showerror('ADB 연결 오류',adb_error)
                    else:self.scan()
                    if engine_error:
                        self.after(500,lambda e=engine_error:messagebox.showwarning(
                            '스크래핑 엔진 설치 실패','ROM 목록 확인은 가능합니다.\n'+e))
                elif msg=='fatal':
                    self._busy(False);self.status_var.set(value)
                    messagebox.showerror('작업 오류',value)
                elif msg=='scanned':
                    self.adb,serial,rows,sync_count,sync_error=value[:5]
                    cleanup_plan=value[5] if len(value)>5 else None
                    cleanup_error=value[6] if len(value)>6 else ''
                    backup_report=value[7] if len(value)>7 else None
                    backup_error=value[8] if len(value)>8 else ''
                    if backup_report is not None:
                        self._backups_cleaned=True
                    self._busy(False);self._paint(rows,self.current)
                    message=f'기기 연결됨 · ROM {len(rows)}개'
                    if sync_count:message+=f' · KNULLI 한글 표시명 {sync_count}개 동기화 (기기 목록 갱신 필요)'
                    if sync_error:message+=' · 한글 표시명 동기화 실패: '+sync_error
                    if cleanup_error:message+=' · 삭제된 게임 검사 실패: '+cleanup_error
                    if backup_report:
                        count=backup_report['device_removed']+backup_report['local_removed']
                        if count:message+=f' · 프로그램 XML 백업 {count}개 삭제'
                    if backup_error:message+=' · 이전 XML 백업 정리 실패: '+backup_error
                    self.status_var.set(message)
                    if cleanup_plan and cleanup_plan.game_count:
                        self.after(150,lambda p=cleanup_plan:self._offer_cleanup(p))
                elif msg=='cleanup-done':
                    self._busy(False)
                    message=(f'정리 완료 · 게임 정보 {value["removed_games"]}개, '
                             f'관련 자원 {value["removed_media"]}개 정리')
                    self.status_var.set(message)
                    if value['warnings']:
                        messagebox.showwarning('일부 자원 정리 실패',
                            message+'\n\n자세한 내용은 work/last_cleanup.json을 확인하세요.')
                    else:
                        messagebox.showinfo('정리 완료',
                            message+'\n\nKNULLI 게임 목록은 기기에서 갱신해 주세요.')
                    self.scan()
                elif msg=='cleanup-failed':
                    self._busy(False)
                    self.status_var.set('자료 정리 실패 · 기존 데이터 상태를 확인하세요.')
                    messagebox.showerror('자료 정리 실패',str(value))
                elif msg=='preview':
                    token,rid,path,error=value
                    if token==self.preview_request_id and self.active() and self.active().rel==rid:
                        self._draw_preview(path,error)
                elif msg=='renamed':
                    old,new=value
                    if old in self.checked:self.checked.remove(old);self.checked.add(new)
                    self.current=new;self._busy(False);self.scan()
                elif msg=='saved':
                    rid,changed=value
                    self._busy(False);self.current=rid
                    self.status_var.set('저장 완료' if changed else '변경 없음')
                    self.scan()
                elif msg=='engine-installed':
                    self._busy(False);self._start_scrape(value)
                elif msg=='work-step':
                    n,total,rid,status,note=value
                    self.progress.configure(value=n if status!='진행 중' else n-1)
                    self.status_var.set(f'{n}/{total} · {rid} · {status}')
                    if self.tree.exists(rid):
                        if status=='진행 중':self.tree.set(rid,'status','… 작업 중')
                        elif status=='unmatched':self.tree.set(rid,'status','✕ 검색 실패')
                        elif status=='error':self.tree.set(rid,'status','✕ 작업 실패')
                elif msg=='work-item':
                    self._update_one(value)
                elif msg=='worked':
                    self._busy(False)
                    results=dict(Counter(r['status'] for r in value))
                    self.status_var.set('완료 · '+str(results))
                    # No full rescan: completed items are already refreshed individually.
                    messagebox.showinfo('작업 완료',f'결과: {results}\n\n필요하면 KNULLI에서 게임 목록을 갱신하세요.')
        except queue.Empty:pass
        self.after(70,self._pump)

    def on_close(self):
        if not self._flush_english_pending():
            messagebox.showwarning('영어 게임명','저장되지 않은 영어 게임명이 있습니다. 내용을 확인하세요.')
            return
        if self.busy:
            messagebox.showwarning('작업 중','기기 파일 작업이 완료되면 종료할 수 있습니다.')
            return
        self.destroy()


if __name__=='__main__':
    # Also support users starting gui.py directly instead of GUI_실행.pyw.
    from auto_update import try_launch_update
    if not try_launch_update(HERE):
        App().mainloop()
