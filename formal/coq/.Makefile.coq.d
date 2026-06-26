theories/Status.vo theories/Status.glob theories/Status.v.beautified theories/Status.required_vo: theories/Status.v 
theories/Status.vio: theories/Status.v 
theories/Status.vos theories/Status.vok theories/Status.required_vos: theories/Status.v 
theories/Event.vo theories/Event.glob theories/Event.v.beautified theories/Event.required_vo: theories/Event.v theories/Status.vo
theories/Event.vio: theories/Event.v theories/Status.vio
theories/Event.vos theories/Event.vok theories/Event.required_vos: theories/Event.v theories/Status.vos
theories/Confidence.vo theories/Confidence.glob theories/Confidence.v.beautified theories/Confidence.required_vo: theories/Confidence.v theories/Event.vo
theories/Confidence.vio: theories/Confidence.v theories/Event.vio
theories/Confidence.vos theories/Confidence.vok theories/Confidence.required_vos: theories/Confidence.v theories/Event.vos
theories/Chain.vo theories/Chain.glob theories/Chain.v.beautified theories/Chain.required_vo: theories/Chain.v theories/Status.vo theories/Event.vo theories/Confidence.vo
theories/Chain.vio: theories/Chain.v theories/Status.vio theories/Event.vio theories/Confidence.vio
theories/Chain.vos theories/Chain.vok theories/Chain.required_vos: theories/Chain.v theories/Status.vos theories/Event.vos theories/Confidence.vos
theories/Invariants.vo theories/Invariants.glob theories/Invariants.v.beautified theories/Invariants.required_vo: theories/Invariants.v theories/Status.vo theories/Event.vo theories/Confidence.vo theories/Chain.vo
theories/Invariants.vio: theories/Invariants.v theories/Status.vio theories/Event.vio theories/Confidence.vio theories/Chain.vio
theories/Invariants.vos theories/Invariants.vok theories/Invariants.required_vos: theories/Invariants.v theories/Status.vos theories/Event.vos theories/Confidence.vos theories/Chain.vos
theories/CRDT.vo theories/CRDT.glob theories/CRDT.v.beautified theories/CRDT.required_vo: theories/CRDT.v theories/Event.vo theories/Chain.vo
theories/CRDT.vio: theories/CRDT.v theories/Event.vio theories/Chain.vio
theories/CRDT.vos theories/CRDT.vok theories/CRDT.required_vos: theories/CRDT.v theories/Event.vos theories/Chain.vos
iris/event_chain_ra.vo iris/event_chain_ra.glob iris/event_chain_ra.v.beautified iris/event_chain_ra.required_vo: iris/event_chain_ra.v theories/Event.vo theories/Chain.vo
iris/event_chain_ra.vio: iris/event_chain_ra.v theories/Event.vio theories/Chain.vio
iris/event_chain_ra.vos iris/event_chain_ra.vok iris/event_chain_ra.required_vos: iris/event_chain_ra.v theories/Event.vos theories/Chain.vos
iris/concurrent_append.vo iris/concurrent_append.glob iris/concurrent_append.v.beautified iris/concurrent_append.required_vo: iris/concurrent_append.v iris/event_chain_ra.vo
iris/concurrent_append.vio: iris/concurrent_append.v iris/event_chain_ra.vio
iris/concurrent_append.vos iris/concurrent_append.vok iris/concurrent_append.required_vos: iris/concurrent_append.v iris/event_chain_ra.vos
