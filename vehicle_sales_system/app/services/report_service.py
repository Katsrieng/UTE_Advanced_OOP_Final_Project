"""Report period validation and dashboard statistics."""

from datetime import date, timedelta


class ReportService:
    def __init__(self, repository):
        self.repository = repository

    def analytics(self, start=None, end=None):
        return self.repository.analytics(start, end)

    @staticmethod
    def period(args):
        period = args.get("period", "30")
        start = (
            args.get("from")
            if period == "custom"
            else str(
                date.today()
                - timedelta(days={"today": 0, "7": 6, "30": 29}.get(period, 29))
            )
        )
        end = args.get("to") if period == "custom" else str(date.today())
        error = None
        try:
            if period == "custom" and (
                not start
                or not end
                or date.fromisoformat(start) > date.fromisoformat(end)
            ):
                raise ValueError()
        except ValueError:
            error = "Choose a valid start and end date. The start must come first."
            start = end = str(date.today())
        return dict(period=period, start=start, end=end, error=error)
