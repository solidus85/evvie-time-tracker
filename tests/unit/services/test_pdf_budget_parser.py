"""Unit tests for PDFBudgetParser"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from services.pdf_budget_parser import PDFBudgetParser


class TestPDFBudgetParser:
    """Test suite for PDFBudgetParser"""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database instance"""
        return Mock()
    
    @pytest.fixture
    def parser(self, mock_db):
        """Create a PDFBudgetParser instance with mock database"""
        return PDFBudgetParser(mock_db)
    
    @pytest.fixture
    def sample_pdf_text(self):
        """Sample text extracted from a PDF"""
        return """
        Client Name: Jane Smith PMI: 12345
        Budget Dates: 01/01/2025 - 01/31/2025
        Report Dates: 01/15/2025
        
        Total Budgeted Amount $5,000.00
        Total Usage in Report Period -$3,000.00
        Current Budget Balance $2,000.00
        Usage as of last payment date 60.0%
        Expected usage as of last payment date 48.5%
        
        The total allocation for staffing services is $4,500.00
        
        Doe, John               01/01/25 - 01/31/25    $25.00    100.0    $2,500.00
        Smith, Jane             01/01/25 - 01/31/25    $25.00    20.0     $500.00
        
        RBT Category            Amount
        Transportation          $200.00
        Supplies               $100.00
        """
    
    @pytest.fixture
    def sample_parsed_data(self):
        """Expected parsed data structure"""
        return {
            "report_info": {
                "client_name": "Jane Smith",
                "pmi": "12345",
                "report_date": "2025-01-15"
            },
            "budget_summary": {
                "budget_period_start": "2025-01-01",
                "budget_period_end": "2025-01-31",
                "total_budgeted": 5000.00,
                "total_spent": 3000.00,
                "remaining_balance": 2000.00,
                "utilization_percentage": 60.0,
                "expected_utilization": 48.5
            },
            "category_breakdown": {},
            "employee_spending_summary": {
                "Doe, John": {
                    "total_hours": 100.0,
                    "total_amount": 2500.00
                },
                "Smith, Jane": {
                    "total_hours": 20.0,
                    "total_amount": 500.00
                }
            },
            "staffing_summary": {
                "total_allocation": 4500.00
            }
        }
    
    # Test basic parsing
    @patch('pdfplumber.open')
    def test_parse_spending_report(self, mock_pdfplumber, parser, sample_pdf_text):
        """Test parsing a PDF spending report"""
        # Mock PDF pages
        mock_page = Mock()
        mock_page.extract_text.return_value = sample_pdf_text
        
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__.return_value = mock_pdf
        mock_pdf.__exit__.return_value = None
        
        mock_pdfplumber.return_value = mock_pdf
        
        result = parser.parse_spending_report('/fake/path.pdf')
        
        assert 'report_info' in result
        assert 'budget_summary' in result
        assert 'employee_spending_summary' in result
        mock_pdfplumber.assert_called_once_with('/fake/path.pdf')
    
    def test_parse_text_client_info(self, parser):
        """Test parsing client information from text"""
        text = "Client Name: Jane Smith PMI: 12345\n"
        result = parser._parse_text(text)
        
        assert result['report_info']['client_name'] == 'Jane Smith'
        assert result['report_info']['pmi'] == '12345'
    
    def test_parse_text_client_name_no_pmi(self, parser):
        """Test parsing client name when PMI is not on same line"""
        text = "Client Name: Jane Smith\nPMI: 12345\n"
        result = parser._parse_text(text)
        
        assert result['report_info']['client_name'] == 'Jane Smith'
        assert result['report_info']['pmi'] == '12345'
    
    def test_parse_text_budget_dates(self, parser):
        """Test parsing budget dates"""
        text = "Budget Dates: 01/01/2025 - 01/31/2025\n"
        result = parser._parse_text(text)
        
        assert result['budget_summary']['budget_period_start'] == '2025-01-01'
        assert result['budget_summary']['budget_period_end'] == '2025-01-31'
    
    def test_parse_text_report_date(self, parser):
        """Test parsing report date"""
        text = "Report Dates: 01/15/2025\n"
        result = parser._parse_text(text)
        
        assert result['report_info']['report_date'] == '2025-01-15'
    
    def test_extract_budget_summary(self, parser):
        """Test extracting budget summary information"""
        text = """
        Total Budgeted Amount $5,000.00
        Total Usage in Report Period -$3,000.00
        Current Budget Balance $2,000.00
        Usage as of last payment date 60.0%
        Expected usage as of last payment date 48.5%
        """
        data = {"budget_summary": {}}
        parser._extract_budget_summary(text, data)
        
        assert data['budget_summary']['total_budgeted'] == 5000.00
        assert data['budget_summary']['total_spent'] == 3000.00
        assert data['budget_summary']['remaining_balance'] == 2000.00
        assert data['budget_summary']['utilization_percentage'] == 60.0
        assert data['budget_summary']['expected_utilization'] == 48.5
    
    def test_extract_staffing_summary(self, parser):
        """Test extracting staffing summary"""
        text = "The total allocation for staffing services is $4,500.00"
        data = {"staffing_summary": {}}
        parser._extract_staffing_summary(text, data)
        
        assert data['staffing_summary']['total_allocation'] == 4500.00
    
    def test_extract_employee_spending(self, parser):
        """Test extracting employee spending details"""
        # The actual format the parser expects
        text = """
        Doe, John            01/01/25 - 01/31/25    $25.00    100.0    $2,500.00
        Smith, Jane          01/01/25 - 01/31/25    $25.00    20.0     $500.00
        Johnson, Bob         01/01/25 - 01/31/25    $25.00    40.5     $1,012.50
        """
        data = {"employee_spending_summary": {}, "report_info": {}}
        parser._extract_employee_spending(text, data)
        
        assert 'Doe, John' in data['employee_spending_summary']
        assert data['employee_spending_summary']['Doe, John']['total_hours'] == 100.0
        assert data['employee_spending_summary']['Doe, John']['total_amount'] == 2500.00
        
        assert 'Smith, Jane' in data['employee_spending_summary']
        assert data['employee_spending_summary']['Smith, Jane']['total_hours'] == 20.0
        
        assert 'Johnson, Bob' in data['employee_spending_summary']
        assert data['employee_spending_summary']['Johnson, Bob']['total_hours'] == 40.5
    
    def test_save_budget_report(self, parser, mock_db):
        """Test saving parsed budget report to database"""
        mock_db.fetchone.return_value = {'id': 1}  # Child exists
        mock_db.insert.return_value = 1
        
        report_data = {
            'report_info': {
                'client_name': 'Smith, Jane',
                'report_date': '2025-01-15'
            },
            'budget_summary': {
                'budget_period_start': '2025-01-01',
                'budget_period_end': '2025-01-31',
                'total_budgeted': 5000.00,
                'total_spent': 3000.00
            }
        }
        
        result = parser.save_budget_report(report_data, 'test.pdf')
        
        assert result == 1
        mock_db.insert.assert_called_once()
        call_args = mock_db.insert.call_args[0]
        assert 'INSERT INTO budget_reports' in call_args[0]
    
    def test_save_budget_report_no_matching_child(self, parser, mock_db):
        """Test saving report when no matching child found"""
        mock_db.fetchone.return_value = None  # No matching child
        mock_db.insert.return_value = 1
        
        report_data = {
            'report_info': {
                'client_name': 'Unknown, Person',
                'report_date': '2025-01-15'
            },
            'budget_summary': {
                'budget_period_start': '2025-01-01',
                'budget_period_end': '2025-01-31',
                'total_budgeted': 5000.00,
                'total_spent': 3000.00
            }
        }
        
        result = parser.save_budget_report(report_data, 'test.pdf')
        
        assert result == 1
        # Should still insert with child_id = None
        call_args = mock_db.insert.call_args[0]
        assert call_args[1][0] is None  # child_id should be None
    
    def test_parse_date(self, parser):
        """Test date parsing function"""
        assert parser._parse_date('01/15/2025') == '2025-01-15'
        assert parser._parse_date('12/31/2024') == '2024-12-31'
        assert parser._parse_date('02/01/2025') == '2025-02-01'
    
    def test_parse_date_invalid(self, parser):
        """Test date parsing with invalid input"""
        # The implementation returns the original string if it can't parse
        assert parser._parse_date('invalid') == 'invalid'
        assert parser._parse_date('') == ''
    
    def test_parse_text_missing_data(self, parser):
        """Test parsing text with missing fields"""
        text = "Some random text without expected fields"
        result = parser._parse_text(text)
        
        assert result['report_info'] == {}
        assert result['budget_summary'] == {}
        assert result['employee_spending_summary'] == {}
    
    def test_extract_employee_spending_no_data(self, parser):
        """Test extracting employee spending when no data present"""
        text = "No employee data here"
        data = {"employee_spending_summary": {}}
        parser._extract_employee_spending(text, data)
        
        assert data['employee_spending_summary'] == {}
    
    def test_full_parse_integration(self, parser, sample_pdf_text):
        """Test complete parsing flow with realistic data"""
        result = parser._parse_text(sample_pdf_text)
        
        # Check report info
        assert result['report_info']['client_name'] == 'Jane Smith'
        assert result['report_info']['pmi'] == '12345'
        assert result['report_info']['report_date'] == '2025-01-15'
        
        # Check budget summary
        assert result['budget_summary']['total_budgeted'] == 5000.00
        assert result['budget_summary']['total_spent'] == 3000.00
        assert result['budget_summary']['remaining_balance'] == 2000.00
        
        # Check employee spending
        assert 'Doe, John' in result['employee_spending_summary']
        assert result['employee_spending_summary']['Doe, John']['total_hours'] == 100.0
        
        # Check staffing summary
        assert result['staffing_summary']['total_allocation'] == 4500.00


class TestPDFBudgetParserIntegration:
    """Integration tests for PDFBudgetParser"""
    
    def test_parse_and_save_workflow(self, test_db):
        """Test complete parse and save workflow"""
        parser = PDFBudgetParser(test_db)
        
        # Create test child
        child_id = test_db.insert(
            "INSERT INTO children (name, code, active) VALUES (?, ?, ?)",
            ('Jane Smith', 'JS001', 1)
        )
        
        report_data = {
            'report_info': {
                'client_name': 'Smith, Jane',  # Last, First format
                'pmi': '12345',
                'report_date': '2025-01-15'
            },
            'budget_summary': {
                'budget_period_start': '2025-01-01',
                'budget_period_end': '2025-01-31',
                'total_budgeted': 5000.00,
                'total_spent': 3000.00,
                'remaining_balance': 2000.00,
                'utilization_percentage': 60.0
            },
            'employee_spending_summary': {
                'John Doe': {'total_hours': 100, 'total_amount': 2500}
            }
        }
        
        # Save the report
        report_id = parser.save_budget_report(report_data, 'test.pdf')
        assert report_id is not None
        
        # Verify the report was saved
        saved = test_db.fetchone(
            "SELECT * FROM budget_reports WHERE id = ?",
            (report_id,)
        )
        
        assert saved is not None
        assert saved['child_id'] == child_id
        assert saved['report_date'] == '2025-01-15'
        assert saved['total_budgeted'] == 5000.00
        assert saved['total_spent'] == 3000.00