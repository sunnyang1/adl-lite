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
