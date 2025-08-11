"""
Factory classes for generating test data.
"""
import random
from datetime import datetime, date, time, timedelta
from typing import Optional, Dict, Any

import factory
from factory import fuzzy
from faker import Faker

fake = Faker()


class EmployeeFactory:
    """Factory for creating test employees."""
    
    @staticmethod
    def create(**kwargs) -> Dict[str, Any]:
        """Create a test employee with optional overrides."""
        defaults = {
            'friendly_name': fake.name(),
            'system_name': fake.user_name()[:20],
            'hourly_rate': round(random.uniform(20.0, 50.0), 2),
            'active': 1
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_batch(count: int, **kwargs) -> list:
        """Create multiple test employees."""
        return [EmployeeFactory.create(**kwargs) for _ in range(count)]


class ChildFactory:
    """Factory for creating test children."""
    
    @staticmethod
    def create(**kwargs) -> Dict[str, Any]:
        """Create a test child with optional overrides."""
        defaults = {
            'name': fake.name(),
            'code': f"{fake.random_uppercase_letter()}{fake.random_uppercase_letter()}{random.randint(100, 999)}",
            'active': 1
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_batch(count: int, **kwargs) -> list:
        """Create multiple test children."""
        return [ChildFactory.create(**kwargs) for _ in range(count)]


class ShiftFactory:
    """Factory for creating test shifts."""
    
    @staticmethod
    def create(employee_id: int, child_id: int, **kwargs) -> Dict[str, Any]:
        """Create a test shift with required IDs and optional overrides."""
        base_date = kwargs.get('date', fake.date_between(start_date='-30d', end_date='today'))
        if isinstance(base_date, str):
            base_date = date.fromisoformat(base_date)
        
        start_hour = random.randint(6, 14)
        duration = random.randint(2, 8)
        
        defaults = {
            'employee_id': employee_id,
            'child_id': child_id,
            'date': base_date.isoformat() if isinstance(base_date, date) else base_date,
            'start_time': f"{start_hour:02d}:00:00",
            'end_time': f"{start_hour + duration:02d}:00:00",
            'is_imported': 0,
            'status': random.choice(['confirmed', 'pending', 'cancelled'])
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_week(employee_id: int, child_id: int, start_date: date, **kwargs) -> list:
        """Create shifts for a full week."""
        shifts = []
        for i in range(5):  # Monday to Friday
            shift_date = start_date + timedelta(days=i)
            if shift_date.weekday() < 5:  # Skip weekends
                shifts.append(ShiftFactory.create(
                    employee_id, child_id, 
                    date=shift_date, 
                    **kwargs
                ))
        return shifts


class PayrollPeriodFactory:
    """Factory for creating test payroll periods."""
    
    @staticmethod
    def create(**kwargs) -> Dict[str, Any]:
        """Create a test payroll period (Thursday to Wednesday)."""
        # Find the most recent Thursday
        today = date.today()
        days_since_thursday = (today.weekday() - 3) % 7
        last_thursday = today - timedelta(days=days_since_thursday)
        
        defaults = {
            'start_date': last_thursday.isoformat(),
            'end_date': (last_thursday + timedelta(days=13)).isoformat()
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_sequence(count: int, start_date: Optional[date] = None) -> list:
        """Create a sequence of consecutive payroll periods."""
        if not start_date:
            # Start from beginning of current year
            start_date = date(date.today().year, 1, 1)
            # Adjust to first Thursday
            days_to_thursday = (3 - start_date.weekday()) % 7
            start_date += timedelta(days=days_to_thursday)
        
        periods = []
        current_start = start_date
        
        for _ in range(count):
            period = {
                'start_date': current_start.isoformat(),
                'end_date': (current_start + timedelta(days=13)).isoformat()
            }
            periods.append(period)
            current_start += timedelta(days=14)
        
        return periods


class ExclusionPeriodFactory:
    """Factory for creating test exclusion periods."""
    
    @staticmethod
    def create(**kwargs) -> Dict[str, Any]:
        """Create a test exclusion period."""
        start_date = fake.date_between(start_date='-30d', end_date='+30d')
        end_date = fake.date_between(start_date=start_date, end_date='+60d')
        
        # XOR constraint - either employee or child, not both
        if 'employee_id' not in kwargs and 'child_id' not in kwargs:
            if random.choice([True, False]):
                kwargs['employee_id'] = random.randint(1, 10)
                kwargs['child_id'] = None
            else:
                kwargs['employee_id'] = None
                kwargs['child_id'] = random.randint(1, 10)
        
        defaults = {
            'name': fake.sentence(nb_words=3),
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'start_time': None if random.choice([True, False]) else f"{random.randint(8, 12):02d}:00:00",
            'end_time': None if not kwargs.get('start_time') else f"{random.randint(13, 18):02d}:00:00",
            'employee_id': kwargs.get('employee_id'),
            'child_id': kwargs.get('child_id'),
            'reason': fake.sentence(),
            'active': 1
        }
        defaults.update(kwargs)
        return defaults


class HourLimitFactory:
    """Factory for creating test hour limits."""
    
    @staticmethod
    def create(employee_id: int, child_id: int, **kwargs) -> Dict[str, Any]:
        """Create a test hour limit."""
        defaults = {
            'employee_id': employee_id,
            'child_id': child_id,
            'max_hours_per_week': random.choice([20, 30, 40]),
            'alert_threshold': random.choice([0.8, 0.9, 0.95])
        }
        defaults.update(kwargs)
        return defaults


class BudgetFactory:
    """Factory for creating test budgets."""
    
    @staticmethod
    def create(child_id: int, **kwargs) -> Dict[str, Any]:
        """Create a test budget."""
        period_start = fake.date_between(start_date='-60d', end_date='today')
        period_end = fake.date_between(start_date=period_start, end_date='+90d')
        budget_amount = round(random.uniform(5000, 20000), 2)
        avg_rate = 30.0
        
        defaults = {
            'child_id': child_id,
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat(),
            'budget_amount': budget_amount,
            'budget_hours': round(budget_amount / avg_rate, 1),
            'notes': fake.sentence()
        }
        defaults.update(kwargs)
        return defaults


class EmployeeRateFactory:
    """Factory for creating test employee rates."""
    
    @staticmethod
    def create(employee_id: int, **kwargs) -> Dict[str, Any]:
        """Create a test employee rate."""
        effective_date = fake.date_between(start_date='-365d', end_date='today')
        
        defaults = {
            'employee_id': employee_id,
            'hourly_rate': round(random.uniform(20.0, 50.0), 2),
            'effective_date': effective_date.isoformat(),
            'end_date': None,
            'notes': fake.sentence() if random.choice([True, False]) else None
        }
        defaults.update(kwargs)
        return defaults


class TestDataGenerator:
    """Generate complex test scenarios."""
    
    @staticmethod
    def create_full_scenario(db, num_employees=3, num_children=2, num_weeks=4):
        """Create a complete test scenario with all related data."""
        employees = []
        children = []
        shifts = []
        
        # Create employees
        for i in range(num_employees):
            emp_data = EmployeeFactory.create()
            cursor = db.execute(
                'INSERT INTO employees (friendly_name, system_name, hourly_rate, active) VALUES (?, ?, ?, ?)',
                (emp_data['friendly_name'], emp_data['system_name'], emp_data['hourly_rate'], emp_data['active'])
            )
            emp_data['id'] = cursor.lastrowid
            employees.append(emp_data)
        
        # Create children
        for i in range(num_children):
            child_data = ChildFactory.create()
            cursor = db.execute(
                'INSERT INTO children (name, code, active) VALUES (?, ?, ?)',
                (child_data['name'], child_data['code'], child_data['active'])
            )
            child_data['id'] = cursor.lastrowid
            children.append(child_data)
        
        # Create payroll periods
        periods = PayrollPeriodFactory.create_sequence(num_weeks // 2 + 1)
        for period in periods:
            cursor = db.execute(
                'INSERT INTO payroll_periods (start_date, end_date) VALUES (?, ?)',
                (period['start_date'], period['end_date'])
            )
            period['id'] = cursor.lastrowid
        
        # Create shifts
        start_date = date.fromisoformat(periods[0]['start_date'])
        for week in range(num_weeks):
            week_start = start_date + timedelta(weeks=week)
            for emp in employees[:2]:  # Only first 2 employees have shifts
                for child in children[:2]:  # Only first 2 children have shifts
                    if random.choice([True, False]):  # 50% chance of shift
                        week_shifts = ShiftFactory.create_week(
                            emp['id'], child['id'], week_start
                        )
                        for shift_data in week_shifts:
                            cursor = db.execute(
                                '''INSERT INTO shifts 
                                   (employee_id, child_id, date, start_time, end_time, is_imported, status) 
                                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                (shift_data['employee_id'], shift_data['child_id'], 
                                 shift_data['date'], shift_data['start_time'], 
                                 shift_data['end_time'], shift_data['is_imported'], 
                                 shift_data['status'])
                            )
                            shift_data['id'] = cursor.lastrowid
                            shifts.append(shift_data)
        
        db.commit()
        
        return {
            'employees': employees,
            'children': children,
            'periods': periods,
            'shifts': shifts
        }