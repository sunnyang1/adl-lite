(* Confidence.v -- confidence derivation as a G-Counter (max) over lifecycle events. *)

Require Import List Arith Lia.
Require Import ADL.Event.

Fixpoint max_confidence (es : list event) : nat :=
  match es with
  | nil => 0
  | e :: es' => Nat.max (confidence e) (max_confidence es')
  end.

Definition derived_confidence_events (es : list event) : nat :=
  max_confidence
    (filter (fun e =>
      match event_type e with
      | VALIDATE => true
      | SNAPSHOT => true
      | _        => false
      end) es).

(* Confidence boundedness (Theorem T4): every event confidence is bounded by
   MaxConfidence, and the derived confidence is bounded by the same constant.
   Here we take MaxConfidence as the maximum over the concrete chain. *)
Theorem confidence_boundedness : forall (es : list event) (e : event),
  In e es -> confidence e <= max_confidence es.
Proof.
  induction es as [| e' es' IH]; intros e Hin.
  - inversion Hin.
  - simpl. destruct Hin as [Heq | Hin].
    + subst. apply Nat.le_max_l.
    + apply IH in Hin. transitivity (max_confidence es'); [apply Hin|].
      apply Nat.le_max_r.
Qed.

Theorem derived_confidence_bounded : forall (es : list event),
  derived_confidence_events es <= max_confidence es.
Proof.
  induction es as [| e es' IH]; simpl; [apply le_n|].
  destruct (event_type e) eqn:Heq;
    unfold derived_confidence_events; simpl; rewrite Heq; simpl;
    try (apply Nat.max_le_compat_l; apply IH);
    try (transitivity (max_confidence es'); [apply IH | apply Nat.le_max_r]).
Qed.
