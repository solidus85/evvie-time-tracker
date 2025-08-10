import pdfplumber
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any

class PDFBudgetParser:
    def __init__(self, db):
        self.db = db
    
    def parse_spending_report(self, pdf_path: str) -> Dict[str, Any]:
        """Parse a spending report PDF and extract budget information"""
        with pdfplumber.open(pdf_path) as pdf:
            # Extract text from all pages
            full_text = ""
            for page in pdf.pages:
                full_text += page.extract_text() + "\n"
            
            # Parse the extracted text
            report_data = self._parse_text(full_text)
            return report_data
    
    def _parse_text(self, text: str) -> Dict[str, Any]:
        """Parse the extracted text and structure the data"""
        data = {
            "report_info": {},
            "budget_summary": {},
            "category_breakdown": {},
            "employee_spending_summary": {},
            "staffing_summary": {}
        }
        
        # Extract client name and PMI
        client_match = re.search(r'Client Name:\s*([^\n]+)', text)
        pmi_match = re.search(r'PMI:\s*(\d+)', text)
        
        if client_match:
            data["report_info"]["client_name"] = client_match.group(1).strip()
        if pmi_match:
            data["report_info"]["pmi"] = pmi_match.group(1).strip()
        
        # Extract budget dates
        budget_dates_match = re.search(r'Budget Dates:\s*(\d+/\d+/\d+)\s*-\s*(\d+/\d+/\d+)', text)
        if budget_dates_match:
            start_date = self._parse_date(budget_dates_match.group(1))
            end_date = self._parse_date(budget_dates_match.group(2))
            data["budget_summary"]["budget_period_start"] = start_date
            data["budget_summary"]["budget_period_end"] = end_date
        
        # Extract report date
        report_date_match = re.search(r'Report Dates:\s*(\d+/\d+/\d+)', text)
        if report_date_match:
            data["report_info"]["report_date"] = self._parse_date(report_date_match.group(1))
        
        # Extract budget summary numbers
        self._extract_budget_summary(text, data)
        
        # Extract staffing summary
        self._extract_staffing_summary(text, data)
        
        # Extract employee spending details
        self._extract_employee_spending(text, data)
        
        return data
    
    def _extract_budget_summary(self, text: str, data: Dict):
        """Extract budget summary information"""
        # Total budgeted amount
        budget_match = re.search(r'Total Budgeted Amount\s*\$?([\d,]+\.?\d*)', text)
        if budget_match:
            data["budget_summary"]["total_budgeted"] = float(budget_match.group(1).replace(',', ''))
        
        # Total usage
        usage_match = re.search(r'Total Usage in Report Period\s*-?\$?([\d,]+\.?\d*)', text)
        if usage_match:
            data["budget_summary"]["total_spent"] = float(usage_match.group(1).replace(',', ''))
        
        # Current balance
        balance_match = re.search(r'Current Budget Balance\s*\$?([\d,]+\.?\d*)', text)
        if balance_match:
            data["budget_summary"]["remaining_balance"] = float(balance_match.group(1).replace(',', ''))
        
        # Usage percentage
        usage_pct_match = re.search(r'Usage as of last payment date\s*([\d.]+)%', text)
        if usage_pct_match:
            data["budget_summary"]["utilization_percentage"] = float(usage_pct_match.group(1))
        
        # Expected usage
        expected_match = re.search(r'Expected usage as of last payment date\s*([\d.]+)%', text)
        if expected_match:
            data["budget_summary"]["expected_utilization"] = float(expected_match.group(1))
    
    def _extract_staffing_summary(self, text: str, data: Dict):
        """Extract staffing summary information"""
        # Total staffing allocation
        staffing_match = re.search(r'total allocation for staffing services is\s*\$?([\d,]+\.?\d*)', text)
        if staffing_match:
            data["staffing_summary"]["total_allocation"] = float(staffing_match.group(1).replace(',', ''))
        
        # Daily usage rate
        daily_rate_match = re.search(r'average daily usage rate for staffing services is\s*\$?([\d,]+\.?\d*)/day', text)
        if daily_rate_match:
            data["staffing_summary"]["daily_usage_rate"] = float(daily_rate_match.group(1).replace(',', ''))
        
        # Remaining staffing balance
        remaining_match = re.search(r'remaining budgeted staffing balance of\s*\$?([\d,]+\.?\d*)', text)
        if remaining_match:
            data["staffing_summary"]["remaining_balance"] = float(remaining_match.group(1).replace(',', ''))
    
    def _extract_employee_spending(self, text: str, data: Dict):
        """Extract employee spending details from the Personal Assistance sections"""
        # Parse Personal Assistance: Paid Parent section
        parent_section = re.search(r'Personal Assistance: Paid Parent of Minor\s*\$?([\d,]+\.?\d*)\s*\$?([\d,]+\.?\d*)', text)
        if parent_section:
            data["category_breakdown"]["personal_assistance_parent"] = {
                "budgeted": float(parent_section.group(1).replace(',', '')),
                "spent": float(parent_section.group(2).replace(',', ''))
            }
        
        # Parse Personal Assistance: Staffing section
        staffing_section = re.search(r'Personal Assistance: Staffing\s*\$?([\d,]+\.?\d*)\s*\$?([\d,]+\.?\d*)', text)
        if staffing_section:
            data["category_breakdown"]["personal_assistance_staffing"] = {
                "budgeted": float(staffing_section.group(1).replace(',', '')),
                "spent": float(staffing_section.group(2).replace(',', ''))
            }
        
        # Extract individual employee spending
        # Pattern to match employee entries with their rates and hours
        employee_pattern = r'([A-Za-z]+),\s*([A-Za-z\s\.]+)\s+\d+/\d+/\d+\s*-\s*\d+/\d+/\d+\s*\$?([\d.]+)\s*([\d.]+)\s*\$?([\d,]+\.?\d*)'
        
        employees = {}
        for match in re.finditer(employee_pattern, text):
            last_name = match.group(1).strip()
            first_name = match.group(2).strip()
            rate = float(match.group(3))
            hours = float(match.group(4))
            amount = float(match.group(5).replace(',', ''))
            
            emp_name = f"{last_name}, {first_name}"
            if emp_name not in employees:
                employees[emp_name] = {
                    "total_hours": 0,
                    "total_amount": 0,
                    "rates": set()
                }
            
            employees[emp_name]["total_hours"] += hours
            employees[emp_name]["total_amount"] += amount
            employees[emp_name]["rates"].add(rate)
        
        # Convert to final format
        for emp_name, emp_data in employees.items():
            data["employee_spending_summary"][emp_name] = {
                "total_hours": round(emp_data["total_hours"], 2),
                "total_amount": round(emp_data["total_amount"], 2),
                "average_rate": round(sum(emp_data["rates"]) / len(emp_data["rates"]), 2) if emp_data["rates"] else 0
            }
    
    def _parse_date(self, date_str: str) -> str:
        """Convert date from M/D/YY format to YYYY-MM-DD"""
        try:
            # Handle both 2-digit and 4-digit years
            if '/' in date_str:
                parts = date_str.split('/')
                month = int(parts[0])
                day = int(parts[1])
                year = int(parts[2])
                
                # Convert 2-digit year to 4-digit
                if year < 100:
                    year = 2000 + year if year < 50 else 1900 + year
                
                return f"{year:04d}-{month:02d}-{day:02d}"
        except:
            return date_str
        return date_str
    
    def save_budget_report(self, report_data: Dict, pdf_filename: str) -> int:
        """Save the parsed budget report to the database"""
        # Find matching child
        child_id = None
        if "client_name" in report_data["report_info"]:
            client_name = report_data["report_info"]["client_name"]
            # Try to match by name (last name, first name format)
            parts = client_name.split(',')
            if len(parts) == 2:
                last_name = parts[0].strip()
                # Look for child with matching last name
                child = self.db.fetchone(
                    "SELECT id FROM children WHERE name LIKE ? OR code = ?",
                    (f"%{last_name}%", client_name)
                )
                if child:
                    child_id = child['id']
        
        # Insert report record
        report_id = self.db.insert(
            """INSERT INTO budget_reports 
               (child_id, report_date, period_start, period_end, 
                total_budgeted, total_spent, remaining_balance, 
                utilization_percent, report_data, pdf_filename)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                child_id,
                report_data["report_info"].get("report_date", datetime.now().strftime('%Y-%m-%d')),
                report_data["budget_summary"].get("budget_period_start", ""),
                report_data["budget_summary"].get("budget_period_end", ""),
                report_data["budget_summary"].get("total_budgeted", 0),
                report_data["budget_summary"].get("total_spent", 0),
                report_data["budget_summary"].get("remaining_balance", 0),
                report_data["budget_summary"].get("utilization_percentage", 0),
                json.dumps(report_data),
                pdf_filename
            )
        )
        
        return report_id
    
    def get_budget_reports(self, child_id: Optional[int] = None) -> List[Dict]:
        """Get all budget reports, optionally filtered by child"""
        query = """
            SELECT br.*, c.name as child_name, c.code as child_code
            FROM budget_reports br
            LEFT JOIN children c ON br.child_id = c.id
            WHERE 1=1
        """
        params = []
        
        if child_id:
            query += " AND br.child_id = ?"
            params.append(child_id)
        
        query += " ORDER BY br.report_date DESC"
        
        return self.db.fetchall(query, params)
    
    def get_report_by_id(self, report_id: int) -> Optional[Dict]:
        """Get a specific budget report by ID"""
        report = self.db.fetchone(
            """SELECT br.*, c.name as child_name, c.code as child_code
               FROM budget_reports br
               LEFT JOIN children c ON br.child_id = c.id
               WHERE br.id = ?""",
            (report_id,)
        )
        
        if report and report['report_data']:
            # Parse JSON data
            report_dict = dict(report)
            report_dict['report_data'] = json.loads(report['report_data'])
            return report_dict
        
        return report
    
    def delete_budget_report(self, report_id: int) -> None:
        """Delete a budget report by ID"""
        self.db.execute(
            "DELETE FROM budget_reports WHERE id = ?",
            (report_id,)
        )