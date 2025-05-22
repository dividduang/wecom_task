import unittest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime

# Assuming WecomTask model is in backend.plugin.wecom_task.model.model_wecom_task
# Adjust the import path if it's different
from backend.plugin.wecom_task.model.model_wecom_task import WecomTask
from backend.plugin.wecom_task.service.tasks import execute_wecom_task

class TestExecuteWecomTask(unittest.TestCase):

    def setUp(self):
        # Basic mock task attributes
        self.mock_task_dict = {
            'id': 1,
            'name': 'Test Task',
            'webhook_url': 'http://fakeurl.com/webhook',
            'message_content': 'Test message content',
            'cron_expression': '* * * * *',
            'message_type': 'text',
            'file_path': None,
            'status': 1,
            'next_run_time': datetime.now()
        }

    @patch('backend.plugin.wecom_task.service.tasks.calculate_next_run_time', return_value=datetime.now())
    @patch('backend.plugin.wecom_task.service.tasks.WechatWorkWebhook')
    @patch('backend.plugin.wecom_task.service.tasks.sessionmaker')
    @patch('backend.plugin.wecom_task.service.tasks.create_engine')
    def test_send_image_success(self, mock_create_engine, mock_sessionmaker, mock_wechat_webhook_constructor, mock_calculate_next_run_time):
        # --- Arrange ---
        # Mock task data
        task_data = self.mock_task_dict.copy()
        task_data['message_type'] = "image"
        task_data['file_path'] = "/fake/path/to/image.png"
        
        mock_task_instance = WecomTask(**task_data)

        # Mock SQLAlchemy session and query
        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_task_instance
        
        # Mock Session context manager
        mock_session_context = MagicMock()
        mock_session_context.__enter__.return_value = mock_session
        mock_session_context.__exit__.return_value = None
        mock_sessionmaker.return_value = mock_session_context # This makes Session() return the context manager

        # Mock WechatWorkWebhook instance and its methods
        mock_webhook_instance = MagicMock()
        mock_webhook_instance.image.return_value = {"errcode": 0, "errmsg": "ok"}
        mock_wechat_webhook_constructor.return_value = mock_webhook_instance

        # --- Act ---
        result = execute_wecom_task(task_id=1)

        # --- Assert ---
        mock_sessionmaker.assert_called_once() # Check if Session was created
        mock_session.execute.assert_called_once() # Check if query was executed
        mock_wechat_webhook_constructor.assert_called_with(mock_task_instance.webhook_url)
        mock_webhook_instance.image.assert_called_once_with(task_data['file_path'])
        mock_calculate_next_run_time.assert_called_once_with(mock_task_instance.cron_expression)
        mock_session.commit.assert_called_once() # For updating next_run_time

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "企业微信消息发送成功")
        self.assertEqual(result["data"], {"errcode": 0, "errmsg": "ok"})

    @patch('backend.plugin.wecom_task.service.tasks.calculate_next_run_time', return_value=datetime.now())
    @patch('backend.plugin.wecom_task.service.tasks.WechatWorkWebhook')
    @patch('backend.plugin.wecom_task.service.tasks.sessionmaker')
    @patch('backend.plugin.wecom_task.service.tasks.create_engine')
    def test_send_file_success(self, mock_create_engine, mock_sessionmaker, mock_wechat_webhook_constructor, mock_calculate_next_run_time):
        # --- Arrange ---
        task_data = self.mock_task_dict.copy()
        task_data['message_type'] = "file"
        task_data['file_path'] = "/fake/path/to/document.pdf"
        
        mock_task_instance = WecomTask(**task_data)

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_task_instance
        
        mock_session_context = MagicMock()
        mock_session_context.__enter__.return_value = mock_session
        mock_session_context.__exit__.return_value = None
        mock_sessionmaker.return_value = mock_session_context

        mock_webhook_instance = MagicMock()
        mock_webhook_instance.file.return_value = {"errcode": 0, "errmsg": "ok"}
        mock_wechat_webhook_constructor.return_value = mock_webhook_instance

        # --- Act ---
        result = execute_wecom_task(task_id=1)

        # --- Assert ---
        mock_sessionmaker.assert_called_once()
        mock_session.execute.assert_called_once()
        mock_wechat_webhook_constructor.assert_called_with(mock_task_instance.webhook_url)
        mock_webhook_instance.file.assert_called_once_with(task_data['file_path'])
        mock_calculate_next_run_time.assert_called_once_with(mock_task_instance.cron_expression)
        mock_session.commit.assert_called_once()

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "企业微信消息发送成功")
        self.assertEqual(result["data"], {"errcode": 0, "errmsg": "ok"})

    @patch('backend.plugin.wecom_task.service.tasks.calculate_next_run_time') # Not called in this path
    @patch('backend.plugin.wecom_task.service.tasks.WechatWorkWebhook')
    @patch('backend.plugin.wecom_task.service.tasks.sessionmaker')
    @patch('backend.plugin.wecom_task.service.tasks.create_engine')
    def test_send_image_missing_file_path(self, mock_create_engine, mock_sessionmaker, mock_wechat_webhook_constructor, mock_calculate_next_run_time):
        # --- Arrange ---
        task_data = self.mock_task_dict.copy()
        task_data['message_type'] = "image"
        task_data['file_path'] = None  # Missing file_path
        
        mock_task_instance = WecomTask(**task_data)

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_task_instance
        
        mock_session_context = MagicMock()
        mock_session_context.__enter__.return_value = mock_session
        mock_session_context.__exit__.return_value = None
        mock_sessionmaker.return_value = mock_session_context

        mock_webhook_instance = MagicMock()
        mock_wechat_webhook_constructor.return_value = mock_webhook_instance

        # --- Act ---
        result = execute_wecom_task(task_id=1)

        # --- Assert ---
        mock_sessionmaker.assert_called_once()
        mock_session.execute.assert_called_once()
        mock_wechat_webhook_constructor.assert_called_with(mock_task_instance.webhook_url) # Webhook is still constructed
        mock_webhook_instance.image.assert_not_called()
        mock_webhook_instance.file.assert_not_called()
        mock_calculate_next_run_time.assert_not_called() # Should not proceed to update next run time
        mock_session.commit.assert_not_called()

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "Image message type requires a file_path.")

    @patch('backend.plugin.wecom_task.service.tasks.calculate_next_run_time') # Not called
    @patch('backend.plugin.wecom_task.service.tasks.WechatWorkWebhook')
    @patch('backend.plugin.wecom_task.service.tasks.sessionmaker')
    @patch('backend.plugin.wecom_task.service.tasks.create_engine')
    def test_send_file_missing_file_path(self, mock_create_engine, mock_sessionmaker, mock_wechat_webhook_constructor, mock_calculate_next_run_time):
        # --- Arrange ---
        task_data = self.mock_task_dict.copy()
        task_data['message_type'] = "file"
        task_data['file_path'] = None  # Missing file_path
        
        mock_task_instance = WecomTask(**task_data)

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_task_instance
        
        mock_session_context = MagicMock()
        mock_session_context.__enter__.return_value = mock_session
        mock_session_context.__exit__.return_value = None
        mock_sessionmaker.return_value = mock_session_context

        mock_webhook_instance = MagicMock()
        mock_wechat_webhook_constructor.return_value = mock_webhook_instance

        # --- Act ---
        result = execute_wecom_task(task_id=1)

        # --- Assert ---
        mock_sessionmaker.assert_called_once()
        mock_session.execute.assert_called_once()
        mock_wechat_webhook_constructor.assert_called_with(mock_task_instance.webhook_url)
        mock_webhook_instance.image.assert_not_called()
        mock_webhook_instance.file.assert_not_called()
        mock_calculate_next_run_time.assert_not_called()
        mock_session.commit.assert_not_called()

        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "File message type requires a file_path.")

    @patch('backend.plugin.wecom_task.service.tasks.calculate_next_run_time') # Not called
    @patch('backend.plugin.wecom_task.service.tasks.WechatWorkWebhook')
    @patch('backend.plugin.wecom_task.service.tasks.sessionmaker')
    @patch('backend.plugin.wecom_task.service.tasks.create_engine')
    def test_send_image_file_not_found(self, mock_create_engine, mock_sessionmaker, mock_wechat_webhook_constructor, mock_calculate_next_run_time):
        # --- Arrange ---
        task_data = self.mock_task_dict.copy()
        task_data['message_type'] = "image"
        task_data['file_path'] = "/fake/path/to/nonexistent_image.png"
        
        mock_task_instance = WecomTask(**task_data)

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_task_instance
        
        mock_session_context = MagicMock()
        mock_session_context.__enter__.return_value = mock_session
        mock_session_context.__exit__.return_value = None
        mock_sessionmaker.return_value = mock_session_context

        mock_webhook_instance = MagicMock()
        mock_webhook_instance.image.side_effect = FileNotFoundError("File not found")
        mock_wechat_webhook_constructor.return_value = mock_webhook_instance

        # --- Act ---
        result = execute_wecom_task(task_id=1)

        # --- Assert ---
        mock_sessionmaker.assert_called_once()
        mock_session.execute.assert_called_once()
        mock_wechat_webhook_constructor.assert_called_with(mock_task_instance.webhook_url)
        mock_webhook_instance.image.assert_called_once_with(task_data['file_path'])
        mock_calculate_next_run_time.assert_not_called()
        mock_session.commit.assert_not_called()

        self.assertFalse(result["success"])
        self.assertTrue("Image file not found" in result["message"]) # Check for part of the message

    @patch('backend.plugin.wecom_task.service.tasks.calculate_next_run_time') # Not called
    @patch('backend.plugin.wecom_task.service.tasks.WechatWorkWebhook')
    @patch('backend.plugin.wecom_task.service.tasks.sessionmaker')
    @patch('backend.plugin.wecom_task.service.tasks.create_engine')
    def test_send_file_file_not_found(self, mock_create_engine, mock_sessionmaker, mock_wechat_webhook_constructor, mock_calculate_next_run_time):
        # --- Arrange ---
        task_data = self.mock_task_dict.copy()
        task_data['message_type'] = "file"
        task_data['file_path'] = "/fake/path/to/nonexistent_file.pdf"
        
        mock_task_instance = WecomTask(**task_data)

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_task_instance
        
        mock_session_context = MagicMock()
        mock_session_context.__enter__.return_value = mock_session
        mock_session_context.__exit__.return_value = None
        mock_sessionmaker.return_value = mock_session_context

        mock_webhook_instance = MagicMock()
        mock_webhook_instance.file.side_effect = FileNotFoundError("File not found")
        mock_wechat_webhook_constructor.return_value = mock_webhook_instance

        # --- Act ---
        result = execute_wecom_task(task_id=1)

        # --- Assert ---
        mock_sessionmaker.assert_called_once()
        mock_session.execute.assert_called_once()
        mock_wechat_webhook_constructor.assert_called_with(mock_task_instance.webhook_url)
        mock_webhook_instance.file.assert_called_once_with(task_data['file_path'])
        mock_calculate_next_run_time.assert_not_called()
        mock_session.commit.assert_not_called()

        self.assertFalse(result["success"])
        self.assertTrue("File not found" in result["message"]) # Check for part of the message

    @patch('backend.plugin.wecom_task.service.tasks.calculate_next_run_time', return_value=datetime.now())
    @patch('backend.plugin.wecom_task.service.tasks.WechatWorkWebhook')
    @patch('backend.plugin.wecom_task.service.tasks.sessionmaker')
    @patch('backend.plugin.wecom_task.service.tasks.create_engine')
    def test_send_text_success(self, mock_create_engine, mock_sessionmaker, mock_wechat_webhook_constructor, mock_calculate_next_run_time):
        # --- Arrange ---
        task_data = self.mock_task_dict.copy()
        task_data['message_type'] = "text"
        # file_path should be None or not relevant for text
        task_data['file_path'] = None 
        
        mock_task_instance = WecomTask(**task_data)

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_task_instance
        
        mock_session_context = MagicMock()
        mock_session_context.__enter__.return_value = mock_session
        mock_session_context.__exit__.return_value = None
        mock_sessionmaker.return_value = mock_session_context

        mock_webhook_instance = MagicMock()
        mock_webhook_instance.text.return_value = {"errcode": 0, "errmsg": "ok"}
        mock_wechat_webhook_constructor.return_value = mock_webhook_instance

        # --- Act ---
        result = execute_wecom_task(task_id=1)

        # --- Assert ---
        mock_wechat_webhook_constructor.assert_called_with(mock_task_instance.webhook_url)
        mock_webhook_instance.text.assert_called_once_with(task_data['message_content'])
        mock_calculate_next_run_time.assert_called_once_with(mock_task_instance.cron_expression)
        mock_session.commit.assert_called_once()

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "企业微信消息发送成功")

    @patch('backend.plugin.wecom_task.service.tasks.calculate_next_run_time', return_value=datetime.now())
    @patch('backend.plugin.wecom_task.service.tasks.WechatWorkWebhook')
    @patch('backend.plugin.wecom_task.service.tasks.sessionmaker')
    @patch('backend.plugin.wecom_task.service.tasks.create_engine')
    def test_send_markdown_success(self, mock_create_engine, mock_sessionmaker, mock_wechat_webhook_constructor, mock_calculate_next_run_time):
        # --- Arrange ---
        task_data = self.mock_task_dict.copy()
        task_data['message_type'] = "markdown"
        # file_path should be None or not relevant for markdown
        task_data['file_path'] = None
        
        mock_task_instance = WecomTask(**task_data)

        mock_session = MagicMock()
        mock_session.execute.return_value.scalar_one_or_none.return_value = mock_task_instance
        
        mock_session_context = MagicMock()
        mock_session_context.__enter__.return_value = mock_session
        mock_session_context.__exit__.return_value = None
        mock_sessionmaker.return_value = mock_session_context

        mock_webhook_instance = MagicMock()
        mock_webhook_instance.markdown.return_value = {"errcode": 0, "errmsg": "ok"}
        mock_wechat_webhook_constructor.return_value = mock_webhook_instance

        # --- Act ---
        result = execute_wecom_task(task_id=1)

        # --- Assert ---
        mock_wechat_webhook_constructor.assert_called_with(mock_task_instance.webhook_url)
        mock_webhook_instance.markdown.assert_called_once_with(task_data['message_content'])
        mock_calculate_next_run_time.assert_called_once_with(mock_task_instance.cron_expression)
        mock_session.commit.assert_called_once()

        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "企业微信消息发送成功")

if __name__ == '__main__':
    unittest.main()
