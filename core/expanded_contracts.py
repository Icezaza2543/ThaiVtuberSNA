"""Additive expanded-v1 contracts. Pure validation; no production I/O."""
from datetime import datetime, timezone
from math import ceil

DATASET_VERSION = 'expanded-v1'
EDGE_TYPES = frozenset({'audience_overlap', 'collaboration', 'production_credit'})
ROLES = frozenset({'performer', 'singer', 'artist', 'rigger'})
FORMATS = frozenset({'PNG', 'Live2D', '3D', 'mixed', 'unknown'})


def count(value, name='count'):
    if type(value) is not int or value < 0:
        raise ValueError(f'{name} must be a non-negative integer')
    return value


def instant(value):
    if not isinstance(value, str):
        raise ValueError('An explicit timestamp is required')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None:
        raise ValueError('Timestamp must include timezone')
    return result.astimezone(timezone.utc)


def request_estimate(channels, videos_per_channel=1000, interaction_videos=48,
                     records_per_video=500, reply_calls=200):
    for v in (channels, videos_per_channel, interaction_videos, records_per_video, reply_calls):
        count(v)
    catalog = channels * (ceil(videos_per_channel / 50) + 1)
    comments = interaction_videos * ceil(records_per_video / 100)
    return {'catalog_base_units': catalog, 'catalog_ceiling_units': ceil(catalog * 1.2),
            'interaction_base_units': comments + reply_calls,
            'interaction_ceiling_units': ceil((comments + reply_calls) * 1.25),
            'combined_record_cap': interaction_videos * records_per_video,
            'catalog_bytes_range': [channels * videos_per_channel * 500,
                                    channels * videos_per_channel * 2000],
            'live_chat_budget': 0, 'live_capacity': 'NOT_MEASURED'}


def capacity_estimate(*, archive_rows, new_viewers=0, new_pairs=0, index_width=0,
                      presence_width=0, control_cells=0, allocated_cells=None,
                      cell_limit=10_000_000):
    values = (archive_rows, new_viewers, new_pairs, index_width, presence_width,
              control_cells, cell_limit)
    for v in values:
        count(v)
    needed = 4 * archive_rows + new_viewers * index_width + new_pairs * presence_width + control_cells
    if (new_viewers and not index_width) or (new_pairs and not presence_width):
        raise ValueError('Schema widths must be measured before estimating growth')
    if allocated_cells is None:
        return {'state': 'NOT_MEASURED', 'additional_cells': needed, 'allocated_cells': None}
    count(allocated_cells)
    return {'state': 'PASS' if allocated_cells + needed <= cell_limit * .8 else 'INSUFFICIENT',
            'additional_cells': needed, 'allocated_cells': allocated_cells,
            'headroom_cells': cell_limit - allocated_cells - needed}
