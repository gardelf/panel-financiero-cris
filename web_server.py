"""
Panel Financiero — Cristina
Servidor Flask con llamadas paralelas a Firefly III
"""
import os
import calendar
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, render_template, jsonify
from firefly_client import FireflyClient

app = Flask(__name__)

# ─────────────────────────────────────────────
# RUTAS
# ─────────────────────────────────────────────

@app.route('/', methods=['GET'])
@app.route('/sandbox2', methods=['GET'])
def index():
    return render_template('panel_cris.html')


@app.route('/data', methods=['GET'])
def panel_data():
    """Devuelve todos los datos financieros del panel como JSON (llamadas paralelas)"""
    try:
        client = FireflyClient()
        now = datetime.now()

        if now.month == 1:
            prev_year, prev_month = now.year - 1, 12
        else:
            prev_year, prev_month = now.year, now.month - 1

        # Ejecutar todas las llamadas a Firefly en paralelo
        results = {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(client.get_monthly_summary, now.year, now.month): 'current_month',
                executor.submit(client.get_monthly_summary, prev_year, prev_month): 'previous_month',
                executor.submit(client.get_yesterday_expenses): 'yesterday',
                executor.submit(client.get_weekly_summary): 'weekly',
                executor.submit(client.get_recurring_fixed_for_month, now.year, now.month): 'recurring',
            }
            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception as e:
                    print(f"❌ Error en {key}: {e}")
                    results[key] = {}

        current_month  = results.get('current_month', {})
        previous_month = results.get('previous_month', {})
        yesterday      = results.get('yesterday', {})
        weekly         = results.get('weekly', {})
        recurring_data = results.get('recurring', {})

        # Cálculos de progreso mensual
        days_in_month      = calendar.monthrange(now.year, now.month)[1]
        days_elapsed       = now.day
        monthly_expenses   = current_month.get('expenses', 0)
        monthly_goal       = 3000.0
        fixed_expenses     = recurring_data.get('total', 0.0)
        fixed_items        = recurring_data.get('items', [])

        # monthly_expenses ya excluye recurrentes (filtrados por recurrence_id en firefly_client)
        # y excluye gastos de Pilates → ES directamente el gasto discrecional del mes
        discretionary_expenses = monthly_expenses
        discretionary_goal     = max(monthly_goal - fixed_expenses, 0)

        daily_avg_discr  = discretionary_expenses / days_elapsed if days_elapsed > 0 else 0
        daily_avg_total  = (monthly_expenses + fixed_expenses) / days_elapsed if days_elapsed > 0 else 0
        projected_total  = daily_avg_total * days_in_month
        projected_discr  = daily_avg_discr * days_in_month

        proportional_target = (discretionary_goal / days_in_month) * days_elapsed if days_in_month > 0 else 0
        deviation           = discretionary_expenses - proportional_target
        deviation_pct       = (deviation / proportional_target * 100) if proportional_target > 0 else 0

        monthly_progress = {
            'days_in_month':          days_in_month,
            'days_elapsed':           days_elapsed,
            'days_remaining':         days_in_month - days_elapsed,
            'progress_pct':           round((days_elapsed / days_in_month) * 100, 1),
            'expenses_accumulated':   round(monthly_expenses, 2),
            'fixed_expenses':         round(fixed_expenses, 2),
            'fixed_items':            fixed_items,
            'discretionary_expenses': round(discretionary_expenses, 2),
            'daily_average':          round(daily_avg_discr, 2),
            'daily_average_total':    round(daily_avg_total, 2),
            'monthly_goal':           monthly_goal,
            'discretionary_goal':     round(discretionary_goal, 2),
            'projected_total':        round(projected_total, 2),
            'projected_discr':        round(projected_discr, 2),
            'proportional_target':    round(proportional_target, 2),
            'deviation':              round(deviation, 2),
            'deviation_pct':          round(deviation_pct, 1),
            'goal_pct':               round((discretionary_expenses / discretionary_goal) * 100, 1) if discretionary_goal > 0 else 0,
            'month_name':             now.strftime('%B %Y')
        }

        return jsonify({
            'success': True,
            'data': {
                'current_month':  current_month,
                'previous_month': previous_month,
                'yesterday':      yesterday,
                'weekly':         weekly,
                'monthly_progress': monthly_progress,
                'last_updated':   now.strftime('%Y-%m-%d %H:%M:%S')
            }
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/mes-detalle', methods=['GET'])
def mes_detalle():
    """Devuelve el detalle de transacciones discrecionales del mes actual para el desplegable"""
    try:
        client = FireflyClient()
        now = datetime.now()

        start_date = datetime(now.year, now.month, 1)
        if now.month == 12:
            end_date = datetime(now.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(now.year, now.month + 1, 1) - timedelta(days=1)

        params = {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d'),
            'type': 'withdrawal'
        }

        data = client._make_request('transactions', params=params)

        if not data or 'data' not in data:
            return jsonify({'success': True, 'transactions': []})

        from firefly_client import _is_excluded
        transactions = []

        for transaction in data['data']:
            attrs = transaction.get('attributes', {})
            trans_list = attrs.get('transactions', [])

            for trans in trans_list:
                if trans.get('type') != 'withdrawal':
                    continue
                if _is_excluded(trans):
                    continue
                amount = abs(float(trans.get('amount', 0)))
                if amount == 0:
                    continue

                # Formatear fecha
                raw_date = trans.get('date', '')
                try:
                    date_obj = datetime.strptime(raw_date[:10], '%Y-%m-%d')
                    date_fmt = date_obj.strftime('%d/%m')
                except Exception:
                    date_fmt = raw_date[:10]

                transactions.append({
                    'description': trans.get('description', ''),
                    'amount': round(amount, 2),
                    'category': trans.get('category_name', '') or 'Sin categoría',
                    'date': date_fmt,
                })

        # Ordenar por importe descendente
        transactions.sort(key=lambda x: -x['amount'])

        return jsonify({'success': True, 'transactions': transactions})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
