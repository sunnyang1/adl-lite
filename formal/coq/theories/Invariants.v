(* Invariants.v -- top-level theorems for the ADL Lite event chain.
   Proofs that are too long for this skeleton are admitted with TODO comments. *)

Require Import List Arith String.
Import ListNotations.
Require Import ADL.Status ADL.Event ADL.Confidence ADL.Chain.

(* Theorem T3: status monotonicity over chains.
   The derived status of a full chain is at least the derived status
   of any prefix. *)
Theorem status_monotonicity : forall (prefix suffix : chain),
  status_leq (derived_status prefix) (derived_status (prefix ++ suffix)).
Proof.
  intros prefix suffix.
  unfold derived_status.
  rewrite !map_app.
  apply status_monotonic.
Qed.

(* Theorem T4: confidence boundedness over chains. *)
Theorem confidence_boundedness_chain : forall (es : chain) (e : event),
  In e es -> confidence e <= max_confidence es.
Proof.
  apply confidence_boundedness.
Qed.

Theorem confidence_boundedness_derived : forall (es : chain),
  derived_confidence es <= max_confidence es.
Proof.
  apply derived_confidence_bounded.
Qed.

(* Theorem T7: well-formedness preservation. *)
Theorem well_formedness_preservation_chain : forall (es : chain) (e : event),
  well_formed es -> valid_append es e -> well_formed (es ++ [e]).
Proof.
  apply well_formedness_preservation.
Qed.


(* ============================================================================= *)
(* E2: Inductive status derivation correctness                                   *)
(* ============================================================================= *)
(* Theorem: for any chain es and any event e, appending e computes the status   *)
(* incrementally as status_max (derived_status es) (StatusOf e), which equals   *)
(* the full LUB recomputation.  This is the formal proof behind the E2          *)
(* experiment (status derivation accuracy).                                      *)

(* Lemma: map distributes over append for event types. *)
Lemma map_event_type_append : forall (es : chain) (e : event),
  map event_type (es ++ [e]) = map event_type es ++ [event_type e].
Proof.
  intros es e. apply map_app.
Qed.

(* Lemma: map distributes over append for StatusOf. *)
Lemma map_StatusOf_append : forall (ss : list adl_event_type) (et : adl_event_type),
  map StatusOf (ss ++ [et]) = map StatusOf ss ++ [StatusOf et].
Proof.
  intros ss et. apply map_app.
Qed.

(* Main E2 theorem: incremental status derivation is correct for arbitrary length. *)
Theorem E2_inductive_status_derivation : forall (es : chain) (e : event),
  derived_status (es ++ [e]) = status_max (derived_status es) (StatusOf (event_type e)).
Proof.
  intros es e.
  unfold derived_status.
  rewrite map_event_type_append.
  rewrite map_StatusOf_append.
  apply status_lub_append.
Qed.

(* Corollary: base case for empty chain. *)
Theorem E2_base_case_empty :
  derived_status nil = PROVISIONAL.
Proof.
  unfold derived_status. simpl. reflexivity.
Qed.

(* Corollary: base case for singleton chain. *)
Theorem E2_base_case_singleton : forall (e : event),
  derived_status [e] = StatusOf (event_type e).
Proof.
  intros e.
  unfold derived_status. simpl. destruct (StatusOf (event_type e)); reflexivity.
Qed.

(* Corollary: the incremental CRDT cache update is sound.  This justifies the   *)
(* Python implementation _update_crdt_caches, which only updates the cached      *)
(* order rather than recomputing the full LUB.                                  *)
Corollary E2_incremental_cache_sound :
  forall (es : chain) (e : event),
    derived_status (es ++ [e]) = status_max (derived_status es) (StatusOf (event_type e)).
Proof.
  apply E2_inductive_status_derivation.
Qed.
