import csv
import json
from io import StringIO, BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

class ExportService:
    def __init__(self, db):
        self.db = db
    
    def get_shifts_for_export(self, start_date, end_date, employee_id=None, child_id=None):
        query = """
            SELECT s.*, e.friendly_name as employee_name, e.system_name as employee_system_name,
                   c.name as child_name, c.code as child_code,
                   (julianday(date || ' ' || end_time) - julianday(date || ' ' || start_time)) * 24 as hours
            FROM shifts s
            JOIN employees e ON s.employee_id = e.id
            JOIN children c ON s.child_id = c.id
            WHERE s.date >= ? AND s.date <= ?
        """
        params = [start_date, end_date]
        
        if employee_id:
            query += " AND s.employee_id = ?"
            params.append(employee_id)
        
        if child_id:
            query += " AND s.child_id = ?"
            params.append(child_id)
        
        query += " ORDER BY s.date, s.start_time"
        return self.db.fetchall(query, params)
    
    def export_csv(self, start_date, end_date, employee_id=None, child_id=None):
        shifts = self.get_shifts_for_export(start_date, end_date, employee_id, child_id)
        
        output = StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'Date', 'Child', 'Employee', 'Start Time', 'End Time',
            'Hours', 'Service Code', 'Status', 'Source'
        ])
        
        for shift in shifts:
            date = datetime.strptime(shift['date'], '%Y-%m-%d').strftime('%m/%d/%Y')
            start_time = datetime.strptime(shift['start_time'], '%H:%M:%S').strftime('%I:%M %p')
            end_time = datetime.strptime(shift['end_time'], '%H:%M:%S').strftime('%I:%M %p')
            
            writer.writerow([
                date,
                f"{shift['child_name']} ({shift['child_code']})",
                f"{shift['employee_name']} ({shift['employee_system_name']})",
                start_time,
                end_time,
                f"{shift['hours']:.2f}",
                shift['service_code'] or '',
                shift['status'] or '',
                'Imported' if shift['is_imported'] else 'Manual'
            ])
        
        return output.getvalue()
    
    def export_json(self, start_date, end_date, employee_id=None, child_id=None):
        shifts = self.get_shifts_for_export(start_date, end_date, employee_id, child_id)
        
        data = {
            'export_date': datetime.now().isoformat(),
            'period': {
                'start': start_date,
                'end': end_date
            },
            'shifts': []
        }
        
        for shift in shifts:
            data['shifts'].append({
                'id': shift['id'],
                'date': shift['date'],
                'child': {
                    'id': shift['child_id'],
                    'name': shift['child_name'],
                    'code': shift['child_code']
                },
                'employee': {
                    'id': shift['employee_id'],
                    'name': shift['employee_name'],
                    'system_name': shift['employee_system_name']
                },
                'start_time': shift['start_time'],
                'end_time': shift['end_time'],
                'hours': round(shift['hours'], 2),
                'service_code': shift['service_code'],
                'status': shift['status'],
                'is_imported': shift['is_imported']
            })
        
        total_hours = sum(shift['hours'] for shift in shifts)
        data['summary'] = {
            'total_shifts': len(shifts),
            'total_hours': round(total_hours, 2),
            'imported_shifts': sum(1 for shift in shifts if shift['is_imported']),
            'manual_shifts': sum(1 for shift in shifts if not shift['is_imported'])
        }
        
        return data
    
    def generate_pdf_report(self, start_date, end_date, employee_id=None, child_id=None):
        shifts = self.get_shifts_for_export(start_date, end_date, employee_id, child_id)
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        title = Paragraph(f"Timesheet Report: {start_date} to {end_date}", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.3*inch))
        
        if not shifts:
            elements.append(Paragraph("No shifts found for the specified period.", styles['Normal']))
        else:
            grouped_shifts = {}
            for shift in shifts:
                key = (shift['employee_name'], shift['child_name'])
                if key not in grouped_shifts:
                    grouped_shifts[key] = []
                grouped_shifts[key].append(shift)
            
            for (employee, child), group_shifts in grouped_shifts.items():
                elements.append(Paragraph(f"<b>{employee} - {child}</b>", styles['Heading2']))
                
                data = [['Date', 'Start', 'End', 'Hours', 'Service', 'Status']]
                
                for shift in group_shifts:
                    date = datetime.strptime(shift['date'], '%Y-%m-%d').strftime('%m/%d')
                    start = datetime.strptime(shift['start_time'], '%H:%M:%S').strftime('%I:%M%p')
                    end = datetime.strptime(shift['end_time'], '%H:%M:%S').strftime('%I:%M%p')
                    
                    data.append([
                        date,
                        start,
                        end,
                        f"{shift['hours']:.1f}",
                        (shift['service_code'] or '')[:20],
                        shift['status'] or ''
                    ])
                
                total_hours = sum(s['hours'] for s in group_shifts)
                data.append(['', '', 'Total:', f"{total_hours:.1f}", '', ''])
                
                table = Table(data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ]))
                
                elements.append(table)
                elements.append(Spacer(1, 0.3*inch))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer