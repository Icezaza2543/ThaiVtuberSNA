"""Spawn-safe extraction worker: no journal or storage objects cross this boundary."""
import logging
from collector.outcomes import ExtractionFailure


def extract(adapter, job, limit):
    try:
        if job['source_type'] == 'comment':
            events = adapter.collect_aggregated_events(job, max_comments=limit)
            status = 'SUCCESS' if events else 'EMPTY_RESULT'
            if getattr(adapter, 'last_capture_partial', False):
                status = 'PARTIAL_CAPTURE'
            return {'status': status, 'events': events}
        import json
        checkpoint = json.loads(job['checkpoint']) if job.get('checkpoint') else {}
        result = adapter.collect_live_chat_events(job, max_messages=limit,
                                                  continuation_token=checkpoint.get('continuation'))
        if result['status'] == 'SUCCESS' and not result['events']:
            result['status'] = 'EMPTY_RESULT'
        return result
    except ExtractionFailure as error:
        return {'status': error.status, 'events': []}
    except Exception:
        return {'status': 'EXTRACTION_FAILURE', 'events': []}


def extraction_worker(connection, adapter, job, limit):
    logging.disable(logging.CRITICAL)
    try:
        connection.send(extract(adapter, job, limit))
    finally:
        connection.close()
