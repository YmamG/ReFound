"""Transparent, local rules for the independent Find the best match experience.

No models/APIs/images are used for ranking. Existing report-to-report scoring is
kept in matching.py. This vocabulary is a small explicit Arabic/English glossary,
not semantic AI. Unknown words use literal normalized token overlap.
"""
from dataclasses import dataclass
from datetime import timedelta
import re
import unicodedata

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _

from core.models import Report


_ARABIC = str.maketrans('أإآٱىة٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', 'اااايه01234567890123456789')
_DIACRITICS = re.compile(r'[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06edـ]')


def normalize(value):
    return _DIACRITICS.sub('', unicodedata.normalize('NFKC', value or '').casefold()).translate(_ARABIC)


_GROUPS = {
    'bag': 'bag bags handbag handbags rucksack شنطة شنطه حقيبة حقيبه حقائب شنط',
    'backpack': 'backpack backpacks',
    'wallet': 'wallet wallets purse محفظة محفظه محافظ بوك',
    'keys': 'key keys keyring مفتاح مفاتيح',
    'phone': 'phone phones smartphone mobile جوال هاتف موبايل',
    'laptop': 'laptop laptops computer لابتوب حاسوب كمبيوتر',
    'headphones': 'headphone headphones earphone earphones earbuds سماعة سماعه سماعات',
    'airpods': 'airpods ايربودز إيربودز',
    'charger': 'charger chargers adapter شاحن شواحن',
    'cable': 'cable cables كابل كيبل سلك اسلاك',
    'book': 'book books كتاب كتب',
    'notebook': 'notebook notebooks دفتر دفاتر كراسة كراسه',
    'bottle': 'bottle bottles قارورة قاروره زجاجة زجاجه مطارة مطاره',
    'glasses': 'glasses spectacles sunglasses نظارة نظاره نظارات',
    'watch': 'watch watches ساعة ساعه ساعات',
    'card': 'card cards id بطاقة بطاقه هوية هويه',
    'case': 'case cover جراب غطاء كفر',
    'small': 'small صغير صغيرة صغيره',
    'large': 'large كبير كبيرة كبيره',
    'wireless': 'wireless لاسلكي لاسلكية لاسلكيه',
    'leather': 'leather جلد جلدية جلديه',
    'canvas': 'canvas fabric قماش قماشية قماشيه',
}
_ALIASES = {normalize(word): key for key, words in _GROUPS.items() for word in words.split()}
_OBJECTS = set(_GROUPS) - {'small', 'large', 'wireless', 'leather', 'canvas'}
_COLOR_GROUPS = {
    'black': 'black أسود اسود سوداء', 'white': 'white أبيض ابيض بيضاء',
    'blue': 'blue أزرق ازرق زرقاء', 'navy': 'navy كحلي',
    'red': 'red أحمر احمر حمراء', 'green': 'green أخضر اخضر خضراء',
    'yellow': 'yellow أصفر اصفر صفراء', 'pink': 'pink وردي وردية ورديه زهري',
    'purple': 'purple violet بنفسجي بنفسجية بنفسجيه',
    'gray': 'gray grey رمادي رمادية رماديه', 'brown': 'brown بني بنية بنيه',
    'beige': 'beige بيج', 'orange': 'orange برتقالي برتقالية برتقاليه',
    'silver': 'silver فضي فضية فضيه', 'gold': 'gold golden ذهبي ذهبية ذهبيه',
    'maroon': 'maroon burgundy عنابي', 'olive': 'olive زيتوني',
}
_COLORS = {normalize(word): key for key, words in _COLOR_GROUPS.items() for word in words.split()}
_STOP = {normalize(word) for word in 'the a an and or with for this that from has was are item lost found near my of in at غرض شيء شي مفقود ضائع ضايع فقدت عثرت ابحث عن في عند مع على هذا هذه الذي التي لونه لون لي خاص'.split()}
_PHRASES = {
    'لاب توب': 'laptop', 'حقيبه ظهر': 'backpack',
    'laptop bag': 'bag laptop', 'phone case': 'case phone',
    'laptop charger': 'charger laptop', 'laptop adapter': 'charger laptop',
}


def raw_words(value):
    value = normalize(value)
    for phrase, replacement in _PHRASES.items():
        value = value.replace(phrase, replacement)
    result = []
    for word in re.findall(r'[^\W_]+', value):
        if word.startswith('وال') and len(word) > 5:
            word = word[3:]
        elif word.startswith('ال') and len(word) > 4:
            word = word[2:]
        if len(word) >= 2:
            result.append(word)
    return result


def item_tokens(value):
    result = set()
    for word in raw_words(value):
        if word in _STOP or word in _COLORS:
            continue
        canonical = _ALIASES.get(word, word)
        result.add(canonical)
        if canonical == 'backpack':
            result.add('bag')
        elif canonical == 'airpods':
            result.add('headphones')
    return result


def primary_object(value):
    words = raw_words(value)
    # Accessory phrases use their physical object, not the device they belong to.
    if 'laptop' in [_ALIASES.get(word, word) for word in words]:
        for head in ('bag', 'charger'):
            if head in [_ALIASES.get(word, word) for word in words]:
                return head
    for word in words:
        head = _ALIASES.get(word, word)
        if head in _OBJECTS:
            return {'backpack': 'bag', 'airpods': 'headphones'}.get(head, head)
    return None


def color_tokens(value):
    result = set()
    for word in raw_words(value):
        if word.startswith('و') and word[1:] in _COLORS:
            word = word[1:]
        if word in _COLORS:
            result.add(_COLORS[word])
    return result


def color_similarity(left, right):
    if not (left or '').strip() or not (right or '').strip():
        return 0.0
    a, b = color_tokens(left), color_tokens(right)
    if a and b:
        return len(a & b) / len(a | b)
    return float(normalize(left).strip() == normalize(right).strip())


def room_key(value):
    return re.sub(r'[\W_]+', '', normalize(value))


@dataclass(frozen=True)
class RankedItem:
    report: Report
    score: int
    reasons: tuple[str, ...]
    color_conflict: bool
    raw_score: float


def rank_items(criteria, limit=20):
    """Rank actual eligible reports; require item evidence, never color alone."""
    query = item_tokens(criteria.get('item', ''))
    if not query:
        return []
    primary = primary_object(criteria['item'])
    cutoff = timezone.now() - timedelta(days=settings.REFOUND_ARCHIVE_DAYS)
    reports = Report.objects.filter(is_hidden=False, created_at__gt=cutoff,
        kind=criteria.get('search_kind') or Report.Kind.FOUND).exclude(status=Report.Status.RESOLVED)
    if criteria.get('building'):
        reports = reports.filter(building=criteria['building'])
    reports = reports.only('id', 'kind', 'title', 'description', 'category', 'color',
        'building', 'location', 'classroom', 'event_date', 'image', 'status', 'created_at')
    maximum = 75 + sum(5 for field in ('category', 'location', 'classroom', 'event_date', 'description') if criteria.get(field))
    matches = []
    for report in reports.iterator():
        title_tokens = item_tokens(report.title)
        all_tokens = title_tokens | item_tokens(report.description)
        if not query & all_tokens:
            continue
        report_primary = primary_object(report.title) or primary_object(report.description)
        if primary and report_primary and primary != report_primary:
            continue
        coverage = len(query & all_tokens) / len(query)
        title_coverage = len(query & title_tokens) / len(query)
        points = 50 * (.8 * coverage + .2 * title_coverage)
        reasons = [_('Shared item details')]
        color = color_similarity(criteria['color'], report.color)
        if color:
            points += 25 * color
            reasons.append(_('Same color') if color == 1 else _('Shared colors'))
        if criteria.get('category') and criteria['category'] == report.category:
            points += 5
            reasons.append(_('Same category'))
        if criteria.get('location') and set(raw_words(criteria['location'])) & set(raw_words(report.location)):
            points += 5
            reasons.append(_('Similar general area'))
        if criteria.get('classroom') and room_key(criteria['classroom']) == room_key(report.classroom):
            points += 5
            reasons.append(_('Same classroom'))
        if criteria.get('event_date'):
            days = abs((criteria['event_date'] - report.event_date).days)
            if days <= 7:
                points += 5 * (1 - days / 8)
                reasons.append(_('Dates within seven days'))
        if criteria.get('description'):
            hints = item_tokens(criteria['description'])
            if hints & all_tokens:
                points += 5 * len(hints & all_tokens) / len(hints)
                reasons.append(_('Shared description keywords'))
        raw_score = 100 * points / maximum
        matches.append(RankedItem(report, min(100, round(raw_score)), tuple(reasons),
            bool(report.color.strip() and not color), raw_score))
    return sorted(matches, key=lambda m: (-m.raw_score, m.color_conflict,
        -m.report.created_at.timestamp(), str(m.report.pk)))[:max(1, min(int(limit), 20))]
