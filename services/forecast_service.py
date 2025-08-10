from datetime import datetime, date, timedelta
from services.budget_service import BudgetService
from services.payroll_service import PayrollService

class ForecastService:
    def __init__(self, db):
        self.db = db
        self.budget_service = BudgetService(db)
        self.payroll_service = PayrollService(db)
    
    def get_available_hours(self, child_id, period_start, period_end):
        """Calculate available hours for a child based on budget and actual usage"""
        utilization = self.budget_service.get_budget_utilization(
            child_id, period_start, period_end
        )
        
        if not utilization:
            return {
                'child_id': child_id,
                'period_start': period_start,
                'period_end': period_end,
                'budget_hours': 0,
                'used_hours': 0,
                'available_hours': 0,
                'days_remaining': 0,
                'average_daily_available': 0
            }
        
        # Calculate days remaining in period
        today = date.today()
        end_date = datetime.strptime(period_end, '%Y-%m-%d').date()
        days_remaining = max(0, (end_date - today).days + 1)
        
        available_hours = utilization['hours_remaining']
        avg_daily = available_hours / days_remaining if days_remaining > 0 else 0
        
        return {
            'child_id': child_id,
            'period_start': period_start,
            'period_end': period_end,
            'budget_hours': utilization['budget_hours'],
            'used_hours': utilization['actual_hours'],
            'available_hours': available_hours,
            'days_remaining': days_remaining,
            'average_daily_available': round(avg_daily, 2),
            'utilization_percent': utilization['utilization_percent']
        }
    
    def get_historical_patterns(self, child_id, lookback_days=90):
        """Analyze historical shift patterns for a child"""
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days)
        
        # Get shift data by day of week
        query = """
            SELECT 
                CASE CAST(strftime('%w', date) AS INTEGER)
                    WHEN 0 THEN 'Sunday'
                    WHEN 1 THEN 'Monday'
                    WHEN 2 THEN 'Tuesday'
                    WHEN 3 THEN 'Wednesday'
                    WHEN 4 THEN 'Thursday'
                    WHEN 5 THEN 'Friday'
                    WHEN 6 THEN 'Saturday'
                END as day_of_week,
                CAST(strftime('%w', date) AS INTEGER) as day_num,
                COUNT(*) as shift_count,
                AVG((julianday(date || ' ' || end_time) - 
                     julianday(date || ' ' || start_time)) * 24) as avg_hours
            FROM shifts
            WHERE child_id = ? AND date >= ? AND date <= ?
            GROUP BY day_num
            ORDER BY day_num
        """
        
        patterns = self.db.fetchall(query, (child_id, start_date.isoformat(), 
                                           end_date.isoformat()))
        
        # Get employee distribution
        employee_query = """
            SELECT e.friendly_name, COUNT(*) as shift_count,
                   SUM((julianday(s.date || ' ' || s.end_time) - 
                        julianday(s.date || ' ' || s.start_time)) * 24) as total_hours
            FROM shifts s
            JOIN employees e ON s.employee_id = e.id
            WHERE s.child_id = ? AND s.date >= ? AND s.date <= ?
            GROUP BY e.id
            ORDER BY total_hours DESC
        """
        
        employees = self.db.fetchall(employee_query, (child_id, start_date.isoformat(),
                                                      end_date.isoformat()))
        
        # Calculate weekly average
        weeks = lookback_days / 7
        total_hours = sum(emp['total_hours'] for emp in employees)
        weekly_avg = total_hours / weeks if weeks > 0 else 0
        
        return {
            'child_id': child_id,
            'analysis_period': lookback_days,
            'weekly_patterns': [dict(p) for p in patterns],
            'employee_distribution': [dict(e) for e in employees],
            'weekly_average_hours': round(weekly_avg, 2),
            'total_hours_analyzed': round(total_hours, 2)
        }
    
    def project_hours(self, child_id, projection_days=30):
        """Project future hour needs based on historical patterns"""
        patterns = self.get_historical_patterns(child_id)
        
        if not patterns['weekly_patterns']:
            return {
                'child_id': child_id,
                'projection_days': projection_days,
                'projected_hours': 0,
                'weekly_projection': 0,
                'confidence': 'low',
                'based_on': 'No historical data'
            }
        
        # Calculate projection based on weekly average
        weekly_avg = patterns['weekly_average_hours']
        weeks = projection_days / 7
        projected_total = weekly_avg * weeks
        
        # Determine confidence level based on data quantity
        total_analyzed = patterns['total_hours_analyzed']
        if total_analyzed < 40:
            confidence = 'low'
        elif total_analyzed < 160:
            confidence = 'medium'
        else:
            confidence = 'high'
        
        # Get current period budget for comparison
        current_period = self.payroll_service.get_current_period()
        budget_comparison = None
        
        if current_period:
            available = self.get_available_hours(
                child_id, 
                current_period['start_date'],
                current_period['end_date']
            )
            if available['budget_hours'] > 0:
                budget_comparison = {
                    'current_budget': available['budget_hours'],
                    'projected_need': projected_total,
                    'variance': available['budget_hours'] - projected_total,
                    'sufficient': available['budget_hours'] >= projected_total
                }
        
        return {
            'child_id': child_id,
            'projection_days': projection_days,
            'projected_hours': round(projected_total, 2),
            'weekly_projection': round(weekly_avg, 2),
            'confidence': confidence,
            'based_on': f'{patterns["analysis_period"]} days of history',
            'budget_comparison': budget_comparison
        }
    
    def get_allocation_recommendations(self, period_id):
        """Generate recommendations for hour allocations based on patterns"""
        period = self.db.fetchone(
            "SELECT * FROM payroll_periods WHERE id = ?",
            (period_id,)
        )
        
        if not period:
            return {'error': 'Period not found'}
        
        # Get all active children with budgets
        children_query = """
            SELECT DISTINCT c.id, c.name, cb.budget_hours
            FROM children c
            JOIN child_budgets cb ON c.id = cb.child_id
            WHERE c.active = 1 
            AND cb.period_start <= ? AND cb.period_end >= ?
        """
        
        children = self.db.fetchall(children_query, 
                                  (period['end_date'], period['start_date']))
        
        recommendations = []
        
        for child in children:
            # Get historical patterns
            patterns = self.get_historical_patterns(child['id'])
            
            if not patterns['employee_distribution']:
                continue
            
            # Calculate recommended allocations based on historical distribution
            total_hours = patterns['weekly_average_hours'] * 2  # Two-week period
            
            for emp in patterns['employee_distribution']:
                emp_percent = emp['total_hours'] / patterns['total_hours_analyzed']
                recommended_hours = total_hours * emp_percent
                
                # Get employee ID
                employee = self.db.fetchone(
                    "SELECT id FROM employees WHERE friendly_name = ?",
                    (emp['friendly_name'],)
                )
                
                if employee:
                    recommendations.append({
                        'child_id': child['id'],
                        'child_name': child['name'],
                        'employee_id': employee['id'],
                        'employee_name': emp['friendly_name'],
                        'recommended_hours': round(recommended_hours, 2),
                        'based_on_percent': round(emp_percent * 100, 1),
                        'budget_hours': child['budget_hours']
                    })
        
        return {
            'period_id': period_id,
            'period_start': period['start_date'],
            'period_end': period['end_date'],
            'recommendations': recommendations
        }
    
    def get_forecast_summary(self, period_start, period_end):
        """Generate a comprehensive forecast summary for all children"""
        children = self.db.fetchall(
            "SELECT * FROM children WHERE active = 1"
        )
        
        summary = []
        total_budget_hours = 0
        total_available_hours = 0
        total_projected_hours = 0
        
        for child in children:
            # Get available hours
            available = self.get_available_hours(
                child['id'], period_start, period_end
            )
            
            # Get projection
            days_in_period = (datetime.strptime(period_end, '%Y-%m-%d') - 
                            datetime.strptime(period_start, '%Y-%m-%d')).days + 1
            projection = self.project_hours(child['id'], days_in_period)
            
            if available['budget_hours'] > 0:
                child_summary = {
                    'child_id': child['id'],
                    'child_name': child['name'],
                    'budget_hours': available['budget_hours'],
                    'used_hours': available['used_hours'],
                    'available_hours': available['available_hours'],
                    'projected_need': projection['projected_hours'],
                    'variance': available['available_hours'] - projection['projected_hours'],
                    'utilization_percent': available['utilization_percent'],
                    'risk_level': self._assess_risk(available, projection)
                }
                
                summary.append(child_summary)
                total_budget_hours += available['budget_hours']
                total_available_hours += available['available_hours']
                total_projected_hours += projection['projected_hours']
        
        return {
            'period_start': period_start,
            'period_end': period_end,
            'children': summary,
            'totals': {
                'budget_hours': round(total_budget_hours, 2),
                'available_hours': round(total_available_hours, 2),
                'projected_hours': round(total_projected_hours, 2),
                'variance': round(total_available_hours - total_projected_hours, 2)
            }
        }
    
    def _assess_risk(self, available, projection):
        """Assess risk level based on available vs projected hours"""
        if available['budget_hours'] == 0:
            return 'unknown'
        
        if projection['projected_hours'] == 0:
            return 'low'
        
        variance_percent = ((available['available_hours'] - projection['projected_hours']) / 
                          available['budget_hours'] * 100)
        
        if variance_percent < -10:
            return 'high'  # Over budget
        elif variance_percent < 0:
            return 'medium'  # Slightly over
        elif variance_percent < 20:
            return 'low'  # Within comfortable range
        else:
            return 'very_low'  # Lots of buffer