import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.uix.switch import Switch
import hashlib
import backend  # Updated import
import os
from datetime import datetime
from requests import get
import pickle
import threading
import webbrowser
from flask import Flask, render_template_string, request

kivy.require('2.0.0')

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'login'
        self.is_dark_mode = True
        # Main layout
        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        # Title
        title = Label(text='CSEC Email Login', font_size=24, size_hint_y=None, height=50)
        main_layout.add_widget(title)
        
        # Login form
        form_layout = GridLayout(cols=2, spacing=10, size_hint_y=None)
        form_layout.bind(minimum_height=form_layout.setter('height'))
        
        # Email field
        form_layout.add_widget(Label(text='Email:', size_hint_y=None, height=40))
        self.email_input = TextInput(multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.email_input)
        
        # Password field
        form_layout.add_widget(Label(text='Password:', size_hint_y=None, height=40))
        self.password_input = TextInput(password=True, multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.password_input)
        
        main_layout.add_widget(form_layout)
        
        # Login button
        login_btn = Button(text='Login', size_hint_y=None, height=50)
        login_btn.bind(on_press=self.login)
        main_layout.add_widget(login_btn)
        
        self.add_widget(main_layout)
    
    def login(self, instance):
        email = self.email_input.text.strip()
        password = self.password_input.text
        
        if not email or not password:
            self.show_popup('Error', 'Please enter email and password')
            return
        
        # Hash password with SHA-512
        hashed_password = hashlib.sha512(password.encode()).hexdigest()
        
        # Store login data
        login_data = {
            'email': email,
            'password': hashed_password,
            'timestamp': datetime.now().isoformat()
        }
        
        logined = False
        try:
            auth = get("https://assets.r2.csec.top/email_users.json").json()
            for i in auth:
                if i['username'] == email:
                    if i['password'] == hashed_password:
                        self.show_popup('Success', 'Login successful!')
                        logined = True
                        break
                    else:
                        self.show_popup('Error', 'Incorrect password')
                        return
            
            if not logined:
                self.show_popup('Error', 'User not found')
                return
                
        except Exception as e:
            self.show_popup('Error', f'Authentication failed: {str(e)}')
            return
        
        # Save to storage
        if logined:
            with open('login.pkl','wb') as f:
                pickle.dump(login_data, f)
            # Switch to main screen
            self.manager.current = 'main'
    
    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.8, 0.4))
        popup.open()

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'main'
        
        # Theme colors
        self.light_theme = {
            'bg_primary': (1, 1, 1, 1),
            'bg_secondary': (0.97, 0.97, 0.97, 1),
            'text_primary': (0.13, 0.13, 0.13, 1),
            'text_secondary': (0.42, 0.42, 0.42, 1),
            'button_normal': (0.9, 0.9, 0.9, 1),
            'button_pressed': (0.8, 0.8, 0.8, 1),
            'input_bg': (1, 1, 1, 1),
            'input_text': (0, 0, 0, 1)
        }

        self.dark_theme = {
            'bg_primary': (0.1, 0.1, 0.1, 1),
            'bg_secondary': (0.18, 0.18, 0.18, 1),
            'text_primary': (1, 1, 1, 1),
            'text_secondary': (0.7, 0.7, 0.7, 1),
            'button_normal': (0.3, 0.3, 0.3, 1),
            'button_pressed': (0.4, 0.4, 0.4, 1),
            'input_bg': (0.2, 0.2, 0.2, 1),
            'input_text': (1, 1, 1, 1)
        }

        self.current_theme = self.light_theme
        self.is_dark_mode = False
        
        # Main layout
        main_layout = BoxLayout(orientation='vertical')
        
        # Header
        header = self.create_header()
        main_layout.add_widget(header)
        
        # Tabbed panel
        self.tab_panel = TabbedPanel(do_default_tab=False)
        
        # Inbox tab
        inbox_tab = TabbedPanelItem(text='Inbox')
        inbox_tab.content = self.create_inbox_tab()
        self.tab_panel.add_widget(inbox_tab)

        # Compose tab
        compose_tab = TabbedPanelItem(text='Compose')
        compose_tab.content = self.create_compose_tab()
        self.tab_panel.add_widget(compose_tab)
        
        # Drafts tab
        drafts_tab = TabbedPanelItem(text='Drafts')
        drafts_tab.content = self.create_drafts_tab()
        self.tab_panel.add_widget(drafts_tab)
        
        # Contacts tab
        contacts_tab = TabbedPanelItem(text='Contacts')
        contacts_tab.content = self.create_contacts_tab()
        self.tab_panel.add_widget(contacts_tab)
        
        main_layout.add_widget(self.tab_panel)
        self.add_widget(main_layout)
        
        # Flask server for viewing emails
        self.flask_thread = None
        self.flask_app = None
        self.last_mail_html = ""
        self.flask_port = 5005

        # Load data
        self.load_inbox()
        self.load_drafts()
        self.load_contacts()
    
    def create_header(self):
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, padding=10)
        
        # Title
        title = Label(text='CSEC Email', font_size=20)
        header.add_widget(title)
        
        # Theme toggle
        theme_layout = BoxLayout(orientation='horizontal', size_hint_x=None, width=200)
        theme_label = Label(text='Dark Mode:', size_hint_x=None, width=100)
        self.theme_switch = Switch(size_hint_x=None, width=100)
        self.theme_switch.bind(active=self.toggle_theme)
        
        theme_layout.add_widget(theme_label)
        theme_layout.add_widget(self.theme_switch)
        header.add_widget(theme_layout)
        
        return header
    
    def create_inbox_tab(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        header = Label(text='Inbox', font_size=18, size_hint_y=None, height=40)
        layout.add_widget(header)

        self.inbox_scroll = ScrollView()
        self.inbox_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.inbox_list.bind(minimum_height=self.inbox_list.setter('height'))
        self.inbox_scroll.add_widget(self.inbox_list)
        layout.add_widget(self.inbox_scroll)

        refresh_btn = Button(text='Refresh', size_hint_y=None, height=40)
        refresh_btn.bind(on_press=lambda x: self.load_inbox())
        layout.add_widget(refresh_btn)

        return layout
    
    def create_compose_tab(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Email form
        form_layout = GridLayout(cols=2, spacing=10, size_hint_y=None)
        form_layout.bind(minimum_height=form_layout.setter('height'))
        
        # To field
        form_layout.add_widget(Label(text='To:', size_hint_y=None, height=40))
        self.to_input = TextInput(multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.to_input)
        
        # Subject field
        form_layout.add_widget(Label(text='Subject:', size_hint_y=None, height=40))
        self.subject_input = TextInput(multiline=False, size_hint_y=None, height=40)
        form_layout.add_widget(self.subject_input)
        
        layout.add_widget(form_layout)
        
        # Message field
        layout.add_widget(Label(text='Message:', size_hint_y=None, height=30))
        self.message_input = TextInput(multiline=True, size_hint_y=0.6)
        layout.add_widget(self.message_input)
        
        # Action buttons
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=10)

        send_btn = Button(text='Send', size_hint_y=None, height=50)
        send_btn.bind(on_press=self.send_email)
        button_layout.add_widget(send_btn)

        draft_btn = Button(text='Save Draft', size_hint_y=None, height=50)
        draft_btn.bind(on_press=self.save_draft)
        button_layout.add_widget(draft_btn)

        clear_btn = Button(text='Clear', size_hint_y=None, height=50)
        clear_btn.bind(on_press=self.clear_form)
        button_layout.add_widget(clear_btn)

        layout.add_widget(button_layout)
        
        return layout
    
    def create_drafts_tab(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Header
        header_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        header_layout.add_widget(Label(text='Saved Drafts', font_size=18))
        
        clear_all_btn = Button(text='Clear All', size_hint_x=None, width=120, size_hint_y=None, height=40)
        clear_all_btn.bind(on_press=self.clear_all_drafts)
        header_layout.add_widget(clear_all_btn)
        
        layout.add_widget(header_layout)
        
        # Drafts list
        self.drafts_scroll = ScrollView()
        self.drafts_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.drafts_list.bind(minimum_height=self.drafts_list.setter('height'))
        self.drafts_scroll.add_widget(self.drafts_list)
        
        layout.add_widget(self.drafts_scroll)
        
        return layout
    
    def create_contacts_tab(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Add contact form
        form_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=10)
        
        self.contact_name_input = TextInput(hint_text='Contact name', multiline=False)
        form_layout.add_widget(self.contact_name_input)
        
        self.contact_email_input = TextInput(hint_text='Email address', multiline=False)
        form_layout.add_widget(self.contact_email_input)
        
        add_btn = Button(text='Add', size_hint_x=None, width=100, size_hint_y=None, height=40)
        add_btn.bind(on_press=self.add_contact)
        form_layout.add_widget(add_btn)
        
        layout.add_widget(form_layout)
        
        # Header
        header_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        header_layout.add_widget(Label(text='Saved Contacts', font_size=16))
        
        clear_contacts_btn = Button(text='Clear All', size_hint_x=None, width=120, size_hint_y=None, height=40)
        clear_contacts_btn.bind(on_press=self.clear_all_contacts)
        header_layout.add_widget(clear_contacts_btn)
        
        layout.add_widget(header_layout)
        
        # Contacts list
        self.contacts_scroll = ScrollView()
        self.contacts_list = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.contacts_list.bind(minimum_height=self.contacts_list.setter('height'))
        self.contacts_scroll.add_widget(self.contacts_list)
        
        layout.add_widget(self.contacts_scroll)
        
        return layout
    
    def toggle_theme(self, instance, value):
        self.is_dark_mode = value
        if value:
            self.current_theme = self.dark_theme
            print("Switched to dark theme")
        else:
            self.current_theme = self.light_theme
            print("Switched to light theme")
    
    def send_email(self, instance):
        to = self.to_input.text.strip()
        subject = self.subject_input.text.strip()
        message = self.message_input.text.strip()
        
        if not to or not message:
            self.show_popup('Error', 'Please fill all required fields (To and Message)')
            return
        
        if not self.validate_email(to):
            self.show_popup('Error', 'Please enter a valid email address')
            return
        
        try:
            with open("login.pkl", 'rb') as f:
                login_data = pickle.load(f)
            
            # Show sending popup
            self.show_popup("Info", "Sending email...")
            
            # Send email in a separate thread to avoid blocking UI
            def send_in_thread():
                try:
                    result = backend.send(to, subject, message, login_data["email"])
                    Clock.schedule_once(lambda dt: self.show_popup('Success', result), 0)
                    if "successfully" in result.lower():
                        Clock.schedule_once(lambda dt: self.clear_form(None), 0)
                except Exception as e:
                    Clock.schedule_once(lambda dt: self.show_popup('Error', f'Failed to send email: {str(e)}'), 0)
            
            threading.Thread(target=send_in_thread, daemon=True).start()
            
        except Exception as e:
            self.show_popup('Error', f'Error accessing login data: {str(e)}')
    
    def save_draft(self, instance):
        to = self.to_input.text.strip()
        subject = self.subject_input.text.strip() or 'No Subject'
        message = self.message_input.text.strip()
        
        if not to and not subject and not message:
            self.show_popup('Error', 'Please enter some content to save')
            return
        
        draft_id = str(int(datetime.now().timestamp() * 1000))
        draft_data = {
            'to': to,
            'subject': subject,
            'message': message,
            'date': datetime.now().isoformat()
        }
        
        try:
            with open("drafts.pkl",'rb') as f:
                drafts = pickle.load(f)
        except:
            drafts = {}
        
        drafts[draft_id] = draft_data
        
        with open("drafts.pkl",'wb') as f:
            pickle.dump(drafts, f)
        
        self.load_drafts()
        self.show_popup('Success', 'Draft saved successfully!')
    
    def clear_form(self, instance):
        self.to_input.text = ''
        self.subject_input.text = ''
        self.message_input.text = ''
    
    def load_inbox(self):
        self.inbox_list.clear_widgets()
        try:
            with open("login.pkl", 'rb') as f:
                login_data = pickle.load(f)
            
            # Load inbox in a separate thread
            def load_in_thread():
                try:
                    inbox = backend.getinbox(login_data["email"])
                    Clock.schedule_once(lambda dt: self.update_inbox_ui(inbox), 0)
                except Exception as e:
                    Clock.schedule_once(lambda dt: self.show_inbox_error(str(e)), 0)
            
            threading.Thread(target=load_in_thread, daemon=True).start()
            
            # Show loading message
            loading_label = Label(text='Loading inbox...', size_hint_y=None, height=40)
            self.inbox_list.add_widget(loading_label)
            
        except Exception as e:
            self.inbox_list.add_widget(Label(text=f'Failed to load inbox: {str(e)}', size_hint_y=None, height=40))
    
    def update_inbox_ui(self, inbox):
        self.inbox_list.clear_widgets()
        
        if not inbox:
            self.inbox_list.add_widget(Label(text='No emails in inbox.', size_hint_y=None, height=40))
            return

        for mail in inbox:
            widget = self.create_inbox_mail_widget(mail)
            self.inbox_list.add_widget(widget)
    
    def show_inbox_error(self, error_msg):
        self.inbox_list.clear_widgets()
        self.inbox_list.add_widget(Label(text=f'Failed to load inbox: {error_msg}', size_hint_y=None, height=40))

    def create_inbox_mail_widget(self, mail):
        frm = mail["from"]
        subject = mail["subject"]
        date = mail["date"]
        
        layout = BoxLayout(orientation='vertical', size_hint_y=None, height=110, padding=5)
        
        info_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=30)
        from_label = Label(text=f"From: {frm}", size_hint_x=0.5, text_size=(None, None))
        subject_label = Label(text=f"Subject: {subject}", size_hint_x=0.4, text_size=(None, None))
        date_label = Label(text=f"{date}", size_hint_x=0.2, text_size=(None, None))
        
        info_layout.add_widget(from_label)
        info_layout.add_widget(subject_label)
        info_layout.add_widget(date_label)
        layout.add_widget(info_layout)

        preview = mail["message"][:100] + ('...' if len(mail["message"]) > 100 else '')
        preview_label = Label(text=preview, size_hint_y=None, height=30, text_size=(None, None))
        layout.add_widget(preview_label)

        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=5)
        view_btn = Button(text='View', size_hint_x=None, width=80, size_hint_y=None, height=35)
        view_btn.bind(on_press=lambda x, mail=mail: self.view_inbox_mail(mail))
        button_layout.add_widget(view_btn)
        layout.add_widget(button_layout)
        
        return layout

    def view_inbox_mail(self, mail):
        # Prepare HTML for display
        message = mail['message'].replace('\n','<br>')
        html = f"""
        <html>
        <head>
            <title>{mail['subject']}</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h2 {{ color: #333; }}
                hr {{ margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h2>{mail['subject']}</h2>
            <p><b>From:</b> {mail['from']}</p>
            <p><b>Date:</b> {mail['date']}</p>
            <hr>
            <div>{message}</div>
        </body>
        </html>
        """
        self.last_mail_html = html
        
        if not self.flask_thread or not self.flask_thread.is_alive():
            threading.Thread(target=self.start_flask_server, daemon=True).start()
        
        webbrowser.open(f"http://127.0.0.1:{self.flask_port}/view")

    def start_flask_server(self):
        if self.flask_app is None:
            app = Flask(__name__)

            @app.route('/view')
            def view():
                return self.last_mail_html

            self.flask_app = app

            def run_flask():
                import logging
                log = logging.getLogger('werkzeug')
                log.setLevel(logging.ERROR)
                app.run(port=self.flask_port, debug=False, use_reloader=False, threaded=True)

            self.flask_thread = threading.Thread(target=run_flask, daemon=True)
            self.flask_thread.start()
    
    # ... (rest of the methods remain the same as in original)
    def load_drafts(self):
        self.drafts_list.clear_widgets()
        
        try:
            with open("drafts.pkl", 'rb') as f:
                drafts = pickle.load(f)
                draft_keys = list(drafts.keys())
        except:
            draft_keys = []
        
        if not draft_keys:
            empty_label = Label(text='No drafts saved yet.', size_hint_y=None, height=40)
            self.drafts_list.add_widget(empty_label)
            return
        
        for key in draft_keys:
            try:
                draft = drafts[key]
                draft_widget = self.create_draft_widget(key, draft)
                self.drafts_list.add_widget(draft_widget)
            except:
                continue
    
    def create_draft_widget(self, draft_id, draft):
        layout = BoxLayout(orientation='vertical', size_hint_y=None, height=100, padding=5)
        
        # Draft info
        info_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=30)
        
        subject_label = Label(text=f"Subject: {draft['subject']}")
        info_layout.add_widget(subject_label)
        
        date_label = Label(text=f"Date: {draft['date'][:10]}", size_hint_x=None, width=100)
        info_layout.add_widget(date_label)
        
        layout.add_widget(info_layout)
        
        # To and preview
        to_label = Label(text=f"To: {draft['to'] or 'Not specified'}", size_hint_y=None, height=20)
        layout.add_widget(to_label)
        
        preview = draft['message'][:100] + ('...' if len(draft['message']) > 100 else '')
        preview_label = Label(text=preview, size_hint_y=None, height=30)
        layout.add_widget(preview_label)
        
        # Action buttons
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=5)

        edit_btn = Button(text='Edit', size_hint_x=None, width=80, size_hint_y=None, height=35)
        edit_btn.bind(on_press=lambda x: self.edit_draft(draft_id))
        button_layout.add_widget(edit_btn)

        delete_btn = Button(text='Delete', size_hint_x=None, width=80, size_hint_y=None, height=35)
        delete_btn.bind(on_press=lambda x: self.delete_draft(draft_id))
        button_layout.add_widget(delete_btn)
        
        layout.add_widget(button_layout)
        
        return layout
    
    def edit_draft(self, draft_id):
        try:
            with open("drafts.pkl", 'rb') as f:
                drafts = pickle.load(f)
            
            draft = drafts.get(draft_id)
            if not draft:
                self.show_popup('Error', 'Draft not found')
                return
                
            # Load draft data into compose fields
            self.to_input.text = draft.get('to', '')
            self.subject_input.text = draft.get('subject', '')
            self.message_input.text = draft.get('message', '')
            
            # Switch to compose tab
            self.tab_panel.switch_to(self.tab_panel.tab_list[2])
            
        except Exception as e:
            self.show_popup('Error', f'Failed to edit draft: {str(e)}')
    
    def delete_draft(self, draft_id):
        try:
            with open("drafts.pkl", 'rb') as f:
                drafts = pickle.load(f)
            
            if draft_id in drafts:
                del drafts[draft_id]
                
                with open("drafts.pkl", 'wb') as f:
                    pickle.dump(drafts, f)
                
                self.load_drafts()
                self.show_popup('Success', 'Draft deleted successfully!')
            else:
                self.show_popup('Error', 'Draft not found')
                
        except Exception as e:
            self.show_popup('Error', f'Failed to delete draft: {str(e)}')
    
    def clear_all_drafts(self, instance):
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text='Are you sure you want to clear all drafts?'))
        
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        
        def confirm_clear(btn_instance):
            try:
                with open("drafts.pkl", 'wb') as f:
                    pickle.dump({}, f)
                self.load_drafts()
                self.show_popup('Success', 'All drafts cleared!')
            except Exception as e:
                self.show_popup('Error', f'Failed to clear drafts: {str(e)}')
            popup.dismiss()
        
        def cancel_clear(btn_instance):
            popup.dismiss()
        
        yes_btn = Button(text='Yes')
        yes_btn.bind(on_press=confirm_clear)
        no_btn = Button(text='No')
        no_btn.bind(on_press=cancel_clear)
        
        button_layout.add_widget(yes_btn)
        button_layout.add_widget(no_btn)
        content.add_widget(button_layout)
        
        popup = Popup(title='Confirm Clear All', content=content, size_hint=(0.8, 0.4))
        popup.open()
    
    def add_contact(self, instance):
        name = self.contact_name_input.text.strip()
        email = self.contact_email_input.text.strip()
        
        if not name or not email:
            self.show_popup('Error', 'Please enter both name and email')
            return
        
        if not self.validate_email(email):
            self.show_popup('Error', 'Please enter a valid email address')
            return
        
        try:
            with open("contacts.pkl", 'rb') as f:
                contacts = pickle.load(f)
        except:
            contacts = {}

        # Check if contact already exists
        for contact in contacts.values():
            if contact['email'].lower() == email.lower():
                self.show_popup('Error', 'Contact with this email already exists')
                return
        
        contact_id = str(int(datetime.now().timestamp() * 1000))
        contact_data = {
            'name': name,
            'email': email,
            'date': datetime.now().isoformat()
        }
        
        contacts[contact_id] = contact_data

        with open("contacts.pkl", 'wb') as f:
            pickle.dump(contacts, f)
        
        self.contact_name_input.text = ''
        self.contact_email_input.text = ''
        self.load_contacts()
        self.show_popup('Success', 'Contact added successfully!')
    
    def load_contacts(self):
        self.contacts_list.clear_widgets()
        
        try:
            with open("contacts.pkl", 'rb') as f:
                contacts = pickle.load(f)
                contact_keys = list(contacts.keys())
        except:
            contact_keys = []
        
        if not contact_keys:
            empty_label = Label(text='No contacts saved yet.', size_hint_y=None, height=40)
            self.contacts_list.add_widget(empty_label)
            return
        
        for key in contact_keys:
            try:
                contact = contacts[key]
                contact_widget = self.create_contact_widget(key, contact)
                self.contacts_list.add_widget(contact_widget)
            except:
                continue
    
    def create_contact_widget(self, contact_id, contact):
        layout = BoxLayout(orientation='vertical', size_hint_y=None, height=80, padding=5)
        
        # Contact info
        name_label = Label(text=contact['name'], size_hint_y=None, height=25, font_size=16)
        layout.add_widget(name_label)
        
        email_label = Label(text=contact['email'], size_hint_y=None, height=20)
        layout.add_widget(email_label)
        
        # Action buttons
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=5)

        compose_btn = Button(text='Compose', size_hint_x=None, width=100, size_hint_y=None, height=35)
        compose_btn.bind(on_press=lambda x: self.compose_to_contact(contact['email']))
        button_layout.add_widget(compose_btn)

        delete_btn = Button(text='Delete', size_hint_x=None, width=80, size_hint_y=None, height=35)
        delete_btn.bind(on_press=lambda x: self.delete_contact(contact_id))
        button_layout.add_widget(delete_btn)
        
        layout.add_widget(button_layout)
        
        return layout
    
    def compose_to_contact(self, email):
        self.to_input.text = email
        # Switch to compose tab
        self.tab_panel.switch_to(self.tab_panel.tab_list[2])
        # self.show_popup('Info', f'Composing email to {email}')
    
    def delete_contact(self, contact_id):
        try:
            with open('contacts.pkl', 'rb') as f:
                contacts = pickle.load(f)
            
            if contact_id in contacts:
                del contacts[contact_id]
                
                with open('contacts.pkl', 'wb') as f:
                    pickle.dump(contacts, f)
                
                self.load_contacts()
                self.show_popup('Success', 'Contact deleted successfully!')
            else:
                self.show_popup('Error', 'Contact not found')
                
        except Exception as e:
            self.show_popup('Error', f'Failed to delete contact: {str(e)}')
    
    def clear_all_contacts(self, instance):
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text='Are you sure you want to clear all contacts?'))
        
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
        
        def confirm_clear(btn_instance):
            try:
                with open('contacts.pkl', 'wb') as f:
                    pickle.dump({}, f)
                self.load_contacts()
                self.show_popup('Success', 'All contacts cleared!')
            except Exception as e:
                self.show_popup('Error', f'Failed to clear contacts: {str(e)}')
            popup.dismiss()
        
        def cancel_clear(btn_instance):
            popup.dismiss()
        
        yes_btn = Button(text='Yes')
        yes_btn.bind(on_press=confirm_clear)
        no_btn = Button(text='No')
        no_btn.bind(on_press=cancel_clear)
        
        button_layout.add_widget(yes_btn)
        button_layout.add_widget(no_btn)
        content.add_widget(button_layout)
        
        popup = Popup(title='Confirm Clear All', content=content, size_hint=(0.8, 0.4))
        popup.open()
    
    def validate_email(self, email):
        import re
        pattern = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        return re.match(pattern, email) is not None
    
    def show_popup(self, title, message):
        popup = Popup(title=title, content=Label(text=message), size_hint=(0.8, 0.4))
        popup.open()

class EmailApp(App):
    def build(self):
        # Screen manager
        sm = ScreenManager()
        
        # Check if user is logged in
        if os.path.exists('login.pkl'):
            try:
                users = get("https://assets.r2.csec.top/email_users.json").json()
                with open('login.pkl', 'rb') as f:
                    login_data = pickle.load(f)
                
                logged_in = False
                for user in users:
                    if user["username"] == login_data['email'] and user["password"] == login_data['password']:
                        logged_in = True
                        break
                
                sm.add_widget(LoginScreen())
                sm.add_widget(MainScreen())
                sm.current = 'main' if logged_in else 'login'
                
            except Exception as e:
                print(f"Login validation error: {e}")
                sm.add_widget(LoginScreen())
                sm.add_widget(MainScreen())
                sm.current = 'login'
        else:
            sm.add_widget(LoginScreen())
            sm.add_widget(MainScreen())
            sm.current = 'login'
        
        return sm

if __name__ == '__main__':
    EmailApp().run()
