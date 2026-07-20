(* event_chain_ra.v -- resource algebra for an authoritative event chain.
   This version uses Iris's auth( option(excl) ) camera to model the chain
   as a single ghost variable that can be updated when the caller owns both
   the authoritative and the fragmentary view.

   Extensions: split-lock modelling (auth/frag decomposition), fork RA,
   and well-formedness invariant support. *)

From iris.algebra Require Export auth excl ofe.
From iris.base_logic.lib Require Export own.
From iris.proofmode Require Export proofmode.
Require Export ADL.Event ADL.Chain.

(* The chain is a discrete OFE with Leibniz equality. *)
Notation chainO := (leibnizO chain) (only parsing).

(* Authoritative-exclusive camera for the whole chain.
   The authoritative element represents the current chain;
   the fragmentary element lets clients observe (and, together with the auth,
   update) the chain. *)
Definition event_chainR : cmra := authR (optionUR (exclR chainO)).

(* ------------------------------------------------------------------------- *)
(* Auth / frag decomposition (split-lock model).                            *)
(* ------------------------------------------------------------------------- *)

(* The raw camera element that represents full ownership of a concrete chain
   [es].  Exposed here so that callers can invoke [own_update] explicitly. *)
Definition chain_auth (es : chain) : event_chainR :=
  ● (Some (Excl (es : chainO))) ⋅ ◯ (Some (Excl (es : chainO))).

(* Authoritative-only element: the single writer holds this. *)
Definition chain_auth_only (es : chain) : event_chainR :=
  ● (Some (Excl (es : chainO))).

(* Fragmentary element: any number of readers can hold this. *)
Definition chain_frag (es : chain) : event_chainR :=
  ◯ (Some (Excl (es : chainO))).

(* Ownership of the full chain (auth + frag).  Used when the thread holds
   both the event lock and the cache lock. *)
Definition own_chain `{Hin : !inG Σ event_chainR} (γ : gname) (es : chain) : iProp Σ :=
  own γ (chain_auth es).

(* Ownership of the authoritative part only.  Models the _events_lock. *)
Definition own_chain_auth `{Hin : !inG Σ event_chainR} (γ : gname) (es : chain) : iProp Σ :=
  own γ (chain_auth_only es).

(* Ownership of a fragmentary view.  Models read-only observation. *)
Definition own_chain_frag `{Hin : !inG Σ event_chainR} (γ : gname) (es : chain) : iProp Σ :=
  own γ (chain_frag es).

(* Split full ownership into auth + frag.  This is the ghost-state analogue
   of acquiring the _events_lock while still holding _cache_lock. *)
Lemma chain_auth_frag_split `{Hin : !inG Σ event_chainR} (γ : gname) (es : chain) :
  own_chain γ es ⊣⊢ own_chain_auth γ es ∗ own_chain_frag γ es.
Proof.
  rewrite /own_chain /own_chain_auth /own_chain_frag /chain_auth /chain_auth_only /chain_frag.
  rewrite own_op. done.
Qed.

(* ------------------------------------------------------------------------- *)
(* Fork resource algebra.                                                   *)
(* ------------------------------------------------------------------------- *)

(* After a fork, the parent chain retains auth+frag on its extended history,
   while a fresh child chain gets a new ghost name with its own auth+frag.
   The child starts with a single REGISTER event. *)

(* Two independent chains can coexist in the same context. *)
Definition own_fork_result `{Hin : !inG Σ event_chainR}
  (γ_parent γ_child : gname) (parent : chain) (child : chain) : iProp Σ :=
  own_chain γ_parent parent ∗ own_chain γ_child child.

(* ------------------------------------------------------------------------- *)
(* Well-formedness as a persistent invariant.                               *)
(* ------------------------------------------------------------------------- *)

(* The chain is always well-formed.  This is a persistent fact that can be
   extracted from any ownership of the chain. *)
Definition chain_wf `{Hin : !inG Σ event_chainR} (γ : gname) : iProp Σ :=
  ∃ es, own_chain γ es ∗ ⌜well_formed es⌝.
