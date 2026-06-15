"""
Firefly III API Client
"""
import requests
from datetime import datetime, timedelta
import os
import json

class FireflyClient:
    def __init__(self, base_url=None, token=None):
        self.base_url = base_url or os.getenv('FIREFLY_URL', 'https://firefly-core-production-2d81.up.railway.app')
        self.token = token or os.getenv('FIREFLY_TOKEN', 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJhdWQiOiIxIiwianRpIjoiOTQwNjk2OTdhZTM2YTNiOTM2NDg3ZjVmNzljYjEyMWMyMTM2ZWEzZjZkNmQyNDc1MWQ3ODY3YmI1ZjI1ZDM3YWJlYzM1ODdmY2YzNTJkZDciLCJpYXQiOjE3ODE1MjQ3NjQuMTYwMzcxLCJuYmYiOjE3ODE1MjQ3NjQuMTYwMzczLCJleHAiOjE4MTMwNjA3NjQuMTAxMTE3LCJzdWIiOiIxIiwic2NvcGVzIjpbXX0.a_f4SLFoMQLlawxcrc0NMK-SgfDHP5RFYYEwMkpV4TS6uPH_e7T8BksEGBUl63m16RQU9g-kTHuAqIWtlABIrFXUlRWi5PUD0K34NIvvShDJfNrstUrUG05qSDctQCwj4cp2zOnuv67aqkS6ntzK_uwRA6Gqe6jZbOPd_b-B1taQTMGfGYpQovr0E6L9NCELmmy6tns_MXTELQXgL6FRLVv9wQ1BFGp9zcSJgHJE15m_sXMGgtnyUDpicLCBF13K2TVZr4icCDWSzjdfHndtmucmyqULedhjR95Pfdh-ie4vwLYQ68tjaZJs5llhcNQnSTKQf3umKII9W_ZVURiajqt4MfYe86y_WcgjQaJzN1qbtGNjKGeNSdj-aPXCNv8hVnZaAZtP5zyflvb-UsNqFBJ8r_Mr2cio36t_WwO0TvkeFCcDrp16a6RtIb6mX1nH3Jvk9BmBAk1grLXEP7aW70mEMJfiOzNeydC6syt92F6wCxkOmH3_nYLT2SmwXmqvd7g_jwDVLC-DHxwETF2uFzp8av1dPWhfqdT3ZDcHcS95vmQ8l_ehQ3XPbXUGvB6J68Chthf-ZKHAAr6hQ2pMsr-AMygFQbxoGiC69vpAqY73cfzzA0Ss7w6FQ_T5Yo4QaUYi4N2GwU2Cqnyp5GRC_a0xVqOa7LbmK28es57rUdk')
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def _make_request(self, endpoint, params=None):
        """Make a GET request to Firefly III API with pagination support"""
        try:
            url = f"{self.base_url}/api/v1/{endpoint}"
            
            # Initialize params if None
            if params is None:
                params = {}
            
            # Start with page 1
            params['page'] = 1
            
            all_data = []
            
            while True:
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                # Add current page data
                if 'data' in data:
                    all_data.extend(data['data'])
                
                # Check if there are more pages
                meta = data.get('meta', {})
                pagination = meta.get('pagination', {})
                current_page = pagination.get('current_page', 1)
                total_pages = pagination.get('total_pages', 1)
                
                print(f"📄 Página {current_page}/{total_pages} obtenida ({len(data.get('data', []))} transacciones)")
                
                # If this is the last page, break
                if current_page >= total_pages:
                    break
                
                # Move to next page
                params['page'] = current_page + 1
            
            # Return data in the same format as before
            return {
                'data': all_data,
                'meta': data.get('meta', {})
            }
            
        except Exception as e:
            print(f"❌ Error calling Firefly API: {e}")
            return None
    
    def get_accounts(self):
        """Get all asset accounts"""
        data = self._make_request('accounts', params={'type': 'asset'})
        if data and 'data' in data:
            return data['data']
        return []
    
    def get_balance(self):
        """Get total balance from all asset accounts"""
        accounts = self.get_accounts()
        total_balance = 0
        currency = 'EUR'
        
        for account in accounts:
            attrs = account.get('attributes', {})
            balance = float(attrs.get('current_balance', 0))
            total_balance += balance
            currency = attrs.get('currency_code', 'EUR')
        
        return {
            'total': round(total_balance, 2),
            'currency': currency,
            'accounts_count': len(accounts)
        }
    
    def get_weekly_summary(self):
        """Get summary of transactions for the last 7 days"""
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        params = {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d')
        }
        
        data = self._make_request('transactions', params=params)
        
        if not data or 'data' not in data:
            return {
                'expenses': 0,
                'income': 0,
                'net': 0,
                'currency': 'EUR',
                'transactions_count': 0
            }
        
        expenses = 0
        income = 0
        currency = 'EUR'
        
        for transaction in data['data']:
            attrs = transaction.get('attributes', {})
            transactions = attrs.get('transactions', [])
            
            for trans in transactions:
                amount = float(trans.get('amount', 0))
                trans_type = trans.get('type', '')
                currency = trans.get('currency_code', 'EUR')
                
                if trans_type == 'withdrawal':
                    expenses += abs(amount)
                elif trans_type == 'deposit':
                    income += abs(amount)
        
        return {
            'expenses': round(expenses, 2),
            'income': round(income, 2),
            'net': round(income - expenses, 2),
            'currency': currency,
            'transactions_count': len(data['data'])
        }
    
    def get_monthly_summary(self, year, month):
        """Get summary of transactions for a specific month"""
        # Calculate date range for the month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        params = {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d')
        }
        
        data = self._make_request('transactions', params=params)
        
        if not data or 'data' not in data:
            return {
                'expenses': 0,
                'income': 0,
                'net': 0,
                'currency': 'EUR',
                'transactions_count': 0
            }
        
        expenses = 0
        income = 0
        currency = 'EUR'
        
        for transaction in data['data']:
            attrs = transaction.get('attributes', {})
            transactions = attrs.get('transactions', [])
            
            for trans in transactions:
                amount = float(trans.get('amount', 0))
                trans_type = trans.get('type', '')
                currency = trans.get('currency_code', 'EUR')
                
                if trans_type == 'withdrawal':
                    expenses += abs(amount)
                elif trans_type == 'deposit':
                    income += abs(amount)
        
        return {
            'expenses': round(expenses, 2),
            'income': round(income, 2),
            'net': round(income - expenses, 2),
            'currency': currency,
            'transactions_count': len(data['data'])
        }
    
    def get_yesterday_expenses(self):
        """Get expenses from yesterday"""
        # Calculate yesterday's date
        yesterday = datetime.now() - timedelta(days=1)
        
        params = {
            'start': yesterday.strftime('%Y-%m-%d'),
            'end': yesterday.strftime('%Y-%m-%d'),
            'type': 'withdrawal'
        }
        
        data = self._make_request('transactions', params=params)
        
        if not data or 'data' not in data:
            return {
                'date': yesterday.strftime('%Y-%m-%d'),
                'total': 0,
                'count': 0,
                'expenses': [],
                'currency': 'EUR'
            }
        
        expenses_list = []
        total = 0
        currency = 'EUR'
        
        for transaction in data['data']:
            attrs = transaction.get('attributes', {})
            transactions = attrs.get('transactions', [])
            
            for trans in transactions:
                if trans.get('type') == 'withdrawal':
                    amount = abs(float(trans.get('amount', 0)))
                    total += amount
                    currency = trans.get('currency_code', 'EUR')
                    
                    expenses_list.append({
                        'description': trans.get('description', ''),
                        'amount': amount,
                        'category': trans.get('category_name', 'Sin categoría'),
                        'currency': currency
                    })
        
        return {
            'date': yesterday.strftime('%Y-%m-%d'),
            'total': round(total, 2),
            'count': len(expenses_list),
            'expenses': expenses_list,
            'currency': currency
        }
    
    def get_weekly_transactions_detail(self):
        """Get detailed list of transactions for the last 7 days"""
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        params = {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d')
        }
        
        data = self._make_request('transactions', params=params)
        
        if not data or 'data' not in data:
            return []
        
        transactions_list = []
        
        for transaction in data['data']:
            attrs = transaction.get('attributes', {})
            transactions = attrs.get('transactions', [])
            
            for trans in transactions:
                if trans.get('type') == 'withdrawal':
                    transactions_list.append({
                        'date': trans.get('date', ''),
                        'description': trans.get('description', ''),
                        'amount': abs(float(trans.get('amount', 0))),
                        'category': trans.get('category_name', 'Sin categoría'),
                        'currency': trans.get('currency_code', 'EUR')
                    })
        
        # Sort by date descending
        transactions_list.sort(key=lambda x: x['date'], reverse=True)
        
        return transactions_list
    
    def _load_recurring_expenses(self):
        """Load recurring expenses from configuration file"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'recurring_expenses.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ No se pudieron cargar gastos recurrentes: {e}")
            return {'monthly_expenses': [], 'bimonthly_expenses': [], 'yearly_expenses': []}
    
    def _calculate_recurring_for_month(self, year, month):
        """Calculate recurring expenses for a specific month"""
        config = self._load_recurring_expenses()
        total = 0
        
        # Monthly expenses
        for expense in config.get('monthly_expenses', []):
            total += expense['amount']
        
        # Bimonthly expenses (check if this month is included)
        for expense in config.get('bimonthly_expenses', []):
            if month in expense.get('months', []):
                total += expense['amount']
        
        # Yearly expenses (check if this is the month)
        for expense in config.get('yearly_expenses', []):
            if month == expense.get('month', 0):
                total += expense['amount']
        
        return round(total, 2)
    
    def get_summary(self):
        """Get complete summary for cronograma"""
        now = datetime.now()
        
        # Current month
        current_month = self.get_monthly_summary(now.year, now.month)
        
        # Previous month
        if now.month == 1:
            prev_year = now.year - 1
            prev_month = 12
        else:
            prev_year = now.year
            prev_month = now.month - 1
        previous_month = self.get_monthly_summary(prev_year, prev_month)
        
        # Last 7 days
        weekly = self.get_weekly_summary()
        weekly_detail = self.get_weekly_transactions_detail()
        
        # Next month budgets
        next_month_budgets = self.get_budgets_for_next_month()
        
        # Next month extraordinary expenses
        next_month_extraordinary = self.get_extraordinary_expenses_next_month()
        
        return {
            'current_month': current_month,
            'previous_month': previous_month,
            'weekly': weekly,
            'weekly_detail': weekly_detail,
            'next_month_budgets': next_month_budgets,
            'next_month_extraordinary': next_month_extraordinary,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def get_extraordinary_expenses_next_month(self):
        """Get extraordinary expenses for next month"""
        try:
            # Calculate next month
            now = datetime.now()
            if now.month == 12:
                next_year = now.year + 1
                next_month = 1
            else:
                next_year = now.year
                next_month = now.month + 1
            
            # Get first and last day of next month
            start_date = datetime(next_year, next_month, 1)
            if next_month == 12:
                end_date = datetime(next_year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(next_year, next_month + 1, 1) - timedelta(days=1)
            
            params = {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            }
            
            data = self._make_request('transactions', params=params)
            
            if not data or 'data' not in data:
                return []
            
            extraordinary_expenses = []
            
            for transaction in data['data']:
                attrs = transaction.get('attributes', {})
                transactions = attrs.get('transactions', [])
                
                for trans in transactions:
                    # Only withdrawals with tag "Extraordinario"
                    if trans.get('type') == 'withdrawal':
                        tags = trans.get('tags', [])
                        # Check if "extraordinario" is in the tags
                        has_extraordinary_tag = any(tag.lower() == 'extraordinario' for tag in tags)
                        if has_extraordinary_tag:
                            extraordinary_expenses.append({
                                'date': trans.get('date', ''),
                                'description': trans.get('description', ''),
                                'amount': abs(float(trans.get('amount', 0))),
                                'currency': trans.get('currency_code', 'EUR')
                            })
            
            # Sort by date ascending
            extraordinary_expenses.sort(key=lambda x: x['date'])
            
            return extraordinary_expenses
        
        except Exception as e:
            print(f"❌ Error getting extraordinary expenses: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_budgets_for_next_month(self):
        """Get budgets for next month"""
        try:
            # Calculate next month
            now = datetime.now()
            if now.month == 12:
                next_year = now.year + 1
                next_month = 1
            else:
                next_year = now.year
                next_month = now.month + 1
            
            # Get first and last day of next month
            start_date = datetime(next_year, next_month, 1)
            if next_month == 12:
                end_date = datetime(next_year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(next_year, next_month + 1, 1) - timedelta(days=1)
            
            # Get all budgets
            budgets_data = self._make_request('budgets')
            if not budgets_data or 'data' not in budgets_data:
                return []
            
            budgets_list = []
            
            # For each budget, get its limits
            for budget in budgets_data['data']:
                budget_id = budget['id']
                budget_name = budget['attributes']['name']
                
                # Get budget limits
                limits_data = self._make_request(f'budgets/{budget_id}/limits')
                if limits_data and 'data' in limits_data:
                    for limit in limits_data['data']:
                        limit_attrs = limit['attributes']
                        limit_start = limit_attrs.get('start')
                        limit_end = limit_attrs.get('end')
                        
                        # Check if this limit is for next month
                        if limit_start and limit_end:
                            limit_start_date = datetime.strptime(limit_start, '%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=None)
                            limit_end_date = datetime.strptime(limit_end, '%Y-%m-%dT%H:%M:%S%z').replace(tzinfo=None)
                            
                            # Check if the limit overlaps with next month
                            if (limit_start_date <= end_date and limit_end_date >= start_date):
                                budgets_list.append({
                                    'name': budget_name,
                                    'amount': float(limit_attrs.get('amount', 0)),
                                    'currency': limit_attrs.get('currency_code', 'EUR'),
                                    'start': limit_start,
                                    'end': limit_end
                                })
            
            return budgets_list
        
        except Exception as e:
            print(f"❌ Error getting budgets: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_recurring_fixed_for_month(self, year, month):
        """
        Returns the list of recurring expenses that apply to the given month,
        without any proration. Each recurrence is included only if it fires
        during that month:
          - monthly / ndom / weekly → always fires every month
          - yearly / half-year / quarterly → only if the configured date falls
            within the requested month
        """
        try:
            import calendar
            data = self._make_request('recurrences')
            if not data or 'data' not in data:
                return {'items': [], 'total': 0.0}

            items = []
            total = 0.0

            for rec in data['data']:
                attrs = rec.get('attributes', {})
                if not attrs.get('active', False):
                    continue

                reps = attrs.get('repetitions', [])
                txs = attrs.get('transactions', [])

                for tx in txs:
                    if tx.get('type', '') not in ('withdrawal', ''):
                        continue
                    amt = abs(float(tx.get('amount', 0) or 0))
                    if amt == 0:
                        continue

                    for rep in reps:
                        freq = rep.get('type', '')
                        moment = rep.get('moment', '') or ''

                        fires_this_month = False

                        if freq in ('monthly', 'weekly', 'ndom'):
                            # These always fire every month
                            fires_this_month = True

                        elif freq in ('yearly', 'half-year', 'quarterly'):
                            # moment is a date string like "2026-11-06"
                            # Check if that date falls in the requested month
                            try:
                                m_date = datetime.strptime(moment[:10], '%Y-%m-%d')
                                if m_date.month == month:
                                    fires_this_month = True
                            except Exception:
                                pass

                        if fires_this_month:
                            item = {
                                'title': attrs.get('title', ''),
                                'description': tx.get('description', ''),
                                'amount': round(amt, 2),
                                'category': tx.get('category_name', ''),
                                'frequency': freq,
                                'moment': moment,
                                'tags': tx.get('tags', []),
                            }
                            items.append(item)
                            total += amt
                            break  # only count once per recurrence

            items.sort(key=lambda x: -x['amount'])
            return {'items': items, 'total': round(total, 2)}

        except Exception as e:
            print(f"❌ Error getting recurring fixed expenses: {e}")
            import traceback
            traceback.print_exc()
            return {'items': [], 'total': 0.0}
