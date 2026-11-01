"""P1-native artifact publication; separate durable run completion is explicit."""
from vde.storage import Storage


def publish_internal_result(env, run_id, artifact_id, data, checkpoint):
    mapping = {'staged': 'before_artifact_promotion', 'promoted': 'after_promotion_before_metadata',
               'metadata': 'after_metadata_before_event', 'event': 'after_artifact_event_before_commit'}
    storage = Storage(env.database, env.workspace, checkpoint=lambda stage: checkpoint(mapping[stage]))
    artifact = storage.register_artifact(id=artifact_id, run_id=run_id,
                                         artifact_type='P4_INTERNAL', format='P4_INTERNAL_V2', data=data)
    checkpoint('after_artifact_commit')
    return artifact
