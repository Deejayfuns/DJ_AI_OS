from datetime import datetime


class TrendRecommender:

    def __init__(self, providers=None):

        self.providers = providers or [LocalTrendProvider()]

    def get_global_trends(self, limit=25):

        tracks = []

        for provider in self.providers:
            tracks.extend(provider.fetch())

        ranked = sorted(
            tracks,
            key=lambda item: (
                item.get("trend_score", 0),
                item.get("dj_support", 0),
                item.get("release_heat", 0)
            ),
            reverse=True
        )

        return ranked[:limit]

    def recommend_for_library(self, library, limit=10):

        trends = self.get_global_trends(limit=50)
        genres = {
            str(track.get("genre", "")).upper()
            for track in library
            if track.get("genre")
        }
        roles = {
            str(track.get("role", "")).upper()
            for track in library
            if track.get("role")
        }

        recommendations = []

        for trend in trends:
            genre_match = str(trend.get("genre", "")).upper() in genres
            role_match = str(trend.get("role", "")).upper() in roles
            fit_score = trend.get("trend_score", 0)

            if genre_match:
                fit_score += 12

            if role_match:
                fit_score += 6

            item = dict(trend)
            item["library_fit_score"] = min(100, fit_score)
            item["recommendation_reason"] = self.reason(
                item,
                genre_match,
                role_match
            )
            recommendations.append(item)

        return sorted(
            recommendations,
            key=lambda item: item.get("library_fit_score", 0),
            reverse=True
        )[:limit]

    def reason(self, item, genre_match, role_match):

        reasons = []

        if genre_match:
            reasons.append("arsivindeki turlerle uyumlu")

        if role_match:
            reasons.append("set rolune uygun")

        if item.get("dj_support", 0) >= 80:
            reasons.append("DJ support guclu")

        if item.get("release_heat", 0) >= 80:
            reasons.append("guncel release sicakligi yuksek")

        if not reasons:
            reasons.append("global trend radarinda")

        return ", ".join(reasons)


class LocalTrendProvider:

    def fetch(self):

        today = datetime.now().strftime("%Y-%m-%d")

        return [
            {
                "artist": "Global Radar",
                "title": "Peak Time Signal",
                "genre": "TECH HOUSE",
                "role": "PEAK TIME",
                "bpm": 126,
                "key": "8A",
                "trend_score": 94,
                "dj_support": 91,
                "release_heat": 88,
                "source": "DJ AI Cloud Seed",
                "updated_at": today,
            },
            {
                "artist": "Night System",
                "title": "Warehouse Motion",
                "genre": "TECHNO",
                "role": "DRIVE",
                "bpm": 132,
                "key": "11A",
                "trend_score": 90,
                "dj_support": 86,
                "release_heat": 84,
                "source": "DJ AI Cloud Seed",
                "updated_at": today,
            },
            {
                "artist": "Deep Current",
                "title": "Afterhours Bloom",
                "genre": "DEEP HOUSE",
                "role": "GROOVE",
                "bpm": 123,
                "key": "8A",
                "trend_score": 87,
                "dj_support": 82,
                "release_heat": 79,
                "source": "DJ AI Cloud Seed",
                "updated_at": today,
            },
            {
                "artist": "Afro Circuit",
                "title": "Ritual Drive",
                "genre": "AFRO HOUSE",
                "role": "BUILD",
                "bpm": 122,
                "key": "9A",
                "trend_score": 86,
                "dj_support": 80,
                "release_heat": 83,
                "source": "DJ AI Cloud Seed",
                "updated_at": today,
            },
            {
                "artist": "Melodic Index",
                "title": "Skyline Memory",
                "genre": "MELODIC HOUSE",
                "role": "EMOTIONAL PEAK",
                "bpm": 124,
                "key": "10A",
                "trend_score": 84,
                "dj_support": 78,
                "release_heat": 82,
                "source": "DJ AI Cloud Seed",
                "updated_at": today,
            },
        ]
