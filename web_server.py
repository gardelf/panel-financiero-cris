"""
Panel Financiero — Cristina
Servidor Flask minimalista con un único endpoint: /
"""
import os
import calendar
from datetime import datetime
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
    """Devuelve todos los datos financieros del panel como JSON"""
    try:
        client = FireflyClient()
        now = datetime.now()

        # Mes actual
        current_month = client.get_monthly_summary(now.year, now.month)

        # Mes anterior
        if now.month == 1:
            prev_year, prev_month = now.year - 1, 12
        else:
            prev_year, prev_month = now.year, now.month - 1
        previous_month = client.get_monthly_summary(prev_year, prev_month)

        # Ayer
        yesterday = client.get_yesterday_expenses()

        # Últimos 7 días
        weekly = client.get_weekly_summary()

        # Progreso mensual
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        days_elapsed = now.day
        monthly_expenses = current_month.get('expenses', 0)
        monthly_goal = 3000.0

        # Gastos fijos recurrentes del mes (dinámico, sin prorrateo)
        recurring_data = client.get_recurring_fixed_for_month(now.year, now.month)
        fixed_expenses = recurring_data.get('total', 0.0)
        fixed_items = recurring_data.get('items', [])

        # Discrecional = total - fijos
        discretionary_expenses = max(monthly_expenses - fixed_expenses, 0)
        discretionary_goal = max(monthly_goal - fixed_expenses, 0)

        daily_avg_discr = discretionary_expenses / days_elapsed if days_elapsed > 0 else 0
        daily_avg_total = monthly_expenses / days_elapsed if days_elapsed > 0 else 0

        projected_total = daily_avg_total * days_in_month
        projected_discr = daily_avg_discr * days_in_month

        proportional_target = (discretionary_goal / days_in_month) * days_elapsed
        deviation = discretionary_expenses - proportional_target
        deviation_pct = (deviation / proportional_target * 100) if proportional_target > 0 else 0

        monthly_progress = {
            'days_in_month': days_in_month,
            'days_elapsed': days_elapsed,
            'days_remaining': days_in_month - days_elapsed,
            'progress_pct': round((days_elapsed / days_in_month) * 100, 1),
            'expenses_accumulated': round(monthly_expenses, 2),
            'fixed_expenses': round(fixed_expenses, 2),
            'fixed_items': fixed_items,
            'discretionary_expenses': round(discretionary_expenses, 2),
            'daily_average': round(daily_avg_discr, 2),
            'daily_average_total': round(daily_avg_total, 2),
            'monthly_goal': monthly_goal,
            'discretionary_goal': round(discretionary_goal, 2),
            'projected_total': round(projected_total, 2),
            'projected_discr': round(projected_discr, 2),
            'proportional_target': round(proportional_target, 2),
            'deviation': round(deviation, 2),
            'deviation_pct': round(deviation_pct, 1),
            'goal_pct': round((discretionary_expenses / discretionary_goal) * 100, 1) if discretionary_goal > 0 else 0,
            'month_name': now.strftime('%B %Y')
        }

        return jsonify({
            'success': True,
            'data': {
                'current_month': current_month,
                'previous_month': previous_month,
                'yesterday': yesterday,
                'weekly': weekly,
                'monthly_progress': monthly_progress,
                'last_updated': now.strftime('%Y-%m-%d %H:%M:%S')
            }
        })

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
