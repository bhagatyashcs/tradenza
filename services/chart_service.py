from collections import defaultdict

from services.equity_service import EquityService


class ChartService:

    @staticmethod
    def get_equity_curve(user):

        history = EquityService.get_history(user)

        labels = []
        values = []

        for point in history:

            labels.append(

                point.created_at.strftime(
                    "%d %b"
                )

            )

            values.append(
                point.balance
            )

        return {

            "labels": labels,

            "values": values

        }

    @staticmethod
    def get_daily_profit(user):

        history = EquityService.get_history(
            user
        )

        labels = []
        values = []

        for point in history:

            labels.append(

                point.created_at.strftime(
                    "%d %b"
                )

            )

            values.append(
                point.daily_profit
            )

        return {

            "labels": labels,

            "values": values

        }

    @staticmethod
    def get_monthly_returns(user):

        history = EquityService.get_history(
            user
        )

        monthly = defaultdict(float)

        for point in history:

            key = point.created_at.strftime(
                "%b %Y"
            )

            monthly[key] += point.daily_profit

        return {

            "labels": list(
                monthly.keys()
            ),

            "values": list(
                monthly.values()
            )

        }

    @staticmethod
    def get_win_rate_history(user):

        history = EquityService.get_history(
            user
        )

        labels = []
        values = []

        for point in history:

            labels.append(

                point.created_at.strftime(
                    "%d %b"
                )

            )

            values.append(
                point.win_rate
            )

        return {

            "labels": labels,

            "values": values

        }

    @staticmethod
    def get_dashboard_charts(user):

        return {

            "equity_curve":

                ChartService.get_equity_curve(
                    user
                ),

            "daily_profit":

                ChartService.get_daily_profit(
                    user
                ),

            "monthly_returns":

                ChartService.get_monthly_returns(
                    user
                ),

            "win_rate":

                ChartService.get_win_rate_history(
                    user
                )

        }