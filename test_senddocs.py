#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import os
import sys
import tempfile
import ftplib
from unittest.mock import MagicMock, patch

# Dodaj ścieżkę bieżącego katalogu do sys.path, aby można było importować moduł senddocs
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import senddocs

class TestSendDocs(unittest.TestCase):

    def setUp(self):
        # Utwórz tymczasowy katalog z testowymi plikami
        self.temp_dir = tempfile.mkdtemp()
        self.test_file1_path = os.path.join(self.temp_dir, "test1.html")
        self.test_file2_path = os.path.join(self.temp_dir, "test2.html")
        
        # Utwórz testowe pliki
        with open(self.test_file1_path, "w") as f:
            f.write("Test content 1")
        with open(self.test_file2_path, "w") as f:
            f.write("Test content 2")
        
        # Utwórz podkatalog z plikami
        self.sub_dir = os.path.join(self.temp_dir, "subdir")
        os.makedirs(self.sub_dir)
        self.test_file3_path = os.path.join(self.sub_dir, "test3.html")
        with open(self.test_file3_path, "w") as f:
            f.write("Test content 3")

    def tearDown(self):
        # Usuń tymczasowe pliki i katalogi
        for root, dirs, files in os.walk(self.temp_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.temp_dir)

    @patch('senddocs.ftplib.FTP')
    def test_upload_file(self, mock_ftp):
        """Test funkcji upload_file"""
        # Przygotuj mock
        ftp_instance = mock_ftp.return_value
        
        # Testuj upload_file
        result = senddocs.upload_file(ftp_instance, self.test_file1_path, "test1.html")
        
        # Sprawdź, czy funkcja storbinary została wywołana
        self.assertTrue(ftp_instance.storbinary.called)
        self.assertTrue(result)

    @patch('senddocs.ftplib.FTP')
    def test_upload_directory(self, mock_ftp):
        """Test funkcji upload_directory"""
        # Przygotuj mock
        ftp_instance = mock_ftp.return_value
        ftp_instance.pwd.return_value = "/"
        
        # Testuj upload_directory
        result = senddocs.upload_directory(ftp_instance, self.temp_dir, ".")
        
        # W tej symulacji wszystko powinno się udać
        self.assertTrue(result)
        
        # Powinna być wywołana funkcja cwd
        self.assertTrue(ftp_instance.cwd.called)

    @patch('senddocs.ftplib.FTP')
    def test_main_directory_not_exists(self, mock_ftp):
        """Test funkcji main gdy katalog źródłowy nie istnieje"""
        # Podmień adres lokalnej dokumentacji na nieistniejący
        original_dir = senddocs.LOCAL_DOCS_DIR
        senddocs.LOCAL_DOCS_DIR = "/nieistniejacy/katalog"
        
        # Testuj main
        result = senddocs.main()
        
        # Przywróć oryginalną ścieżkę
        senddocs.LOCAL_DOCS_DIR = original_dir
        
        # Test powinien zwrócić False (niepowodzenie)
        self.assertFalse(result)
        
        # FTP nie powinien być inicjalizowany
        mock_ftp.assert_not_called()

    @patch('senddocs.ftplib.FTP')
    def test_main_success_flow(self, mock_ftp):
        """Test przepływu funkcji main w przypadku sukcesu"""
        # Przygotuj mock
        ftp_instance = mock_ftp.return_value
        ftp_instance.pwd.return_value = "/"
        
        # Podmień adres lokalnej dokumentacji na tymczasowy katalog
        original_dir = senddocs.LOCAL_DOCS_DIR
        senddocs.LOCAL_DOCS_DIR = self.temp_dir
        
        # Testuj main
        result = senddocs.main()
        
        # Przywróć oryginalną ścieżkę
        senddocs.LOCAL_DOCS_DIR = original_dir
        
        # Test powinien zwrócić True (sukces)
        self.assertTrue(result)
        
        # Sprawdź, czy funkcje FTP zostały wywołane
        self.assertTrue(mock_ftp.called)
        self.assertTrue(ftp_instance.login.called)
        self.assertTrue(ftp_instance.cwd.called)
        self.assertTrue(ftp_instance.quit.called)

if __name__ == "__main__":
    unittest.main() 