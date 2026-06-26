(* Chain.v -- EventChain well-formedness and derived status/confidence.
   A chain is an append-only list of events with cryptographic linkage. *)

Require Import List Arith Lia String.
Import ListNotations.
Require Import ADL.Status ADL.Event ADL.Confidence.

Definition chain := list event.

(* True iff no two events in the chain share the same event_id. *)
Fixpoint distinct_ids (es : chain) : Prop :=
  match es with
  | nil => True
  | e :: es' =>
      (forall e', In e' es' -> event_id e <> event_id e') /\ distinct_ids es'
  end.

(* Axiom 1: every event in the chain is structurally valid.
   We model this as non-emptiness of the actor string. *)
Definition axiom_valid_event (e : event) : Prop :=
  actor e <> EmptyString.

(* Axiom 2: ids are strictly increasing, which approximates the
   cryptographic hash chain (each event refers to its predecessor). *)
Fixpoint axiom_increasing_ids (es : chain) : Prop :=
  match es with
  | nil => True
  | e1 :: es' =>
      match es' with
      | nil => True
      | e2 :: es'' => event_id e1 < event_id e2 /\ axiom_increasing_ids es'
      end
  end.

(* Axiom 3: prev linkage.  The first event has no predecessor;
   every subsequent event's prev equals the previous event's id.
   We use an auxiliary fixpoint that threads the expected predecessor id. *)
Fixpoint prev_linkage_aux (es : chain) (prev_id : option nat) : Prop :=
  match es with
  | nil => True
  | e :: es' =>
      prev e = prev_id /\ prev_linkage_aux es' (Some (event_id e))
  end.

Definition axiom_prev_linkage (es : chain) : Prop := prev_linkage_aux es None.

(* Axioms 4-12 are captured as structural / lifecycle placeholders.
   In the full system these include scope ACL, precondition evaluation,
   signature verification, SHACL constraints, status transitions, etc. *)
Definition axiom_scope_acl (es : chain) : Prop := True.
Definition axiom_precondition_eval (es : chain) : Prop := True.
Definition axiom_signature_verification (es : chain) : Prop := True.
Definition axiom_shacl_constraints (es : chain) : Prop := True.
Definition axiom_status_transition (es : chain) : Prop := True.
Definition axiom_confidence_clamped (es : chain) : Prop := True.
Definition axiom_lifecycle_monotonic (es : chain) : Prop := True.
Definition axiom_validator_collusion (es : chain) : Prop := True.
Definition axiom_synthetic_tagging (es : chain) : Prop := True.

Definition well_formed (es : chain) : Prop :=
  (forall e, In e es -> axiom_valid_event e)
  /\ distinct_ids es
  /\ axiom_increasing_ids es
  /\ axiom_prev_linkage es
  /\ axiom_scope_acl es
  /\ axiom_precondition_eval es
  /\ axiom_signature_verification es
  /\ axiom_shacl_constraints es
  /\ axiom_status_transition es
  /\ axiom_confidence_clamped es
  /\ axiom_lifecycle_monotonic es
  /\ axiom_validator_collusion es
  /\ axiom_synthetic_tagging es.

(* Derived status is the LUB over lifecycle event statuses. *)
Definition derived_status (es : chain) : status :=
  status_lub (map StatusOf (map event_type es)).

(* Derived confidence is the max over VALIDATE/SNAPSHOT events. *)
Definition derived_confidence (es : chain) : nat :=
  derived_confidence_events es.

(* A valid append must increase the event_id beyond the current last event
   and link prev to that last event. *)
Definition valid_append (es : chain) (e : event) : Prop :=
  match es with
  | nil =>
      prev e = None /\ axiom_valid_event e
  | _ :: _ =>
      event_id (last es e) < event_id e /\
      prev e = Some (event_id (last es e)) /\
      axiom_valid_event e
  end.

Lemma valid_append_valid_event : forall (es : chain) (e : event),
  valid_append es e -> axiom_valid_event e.
Proof. intros es e Happ. destruct es; simpl in Happ; intuition. Qed.

(* Helper: all events remain valid after append. *)
Lemma all_events_valid_append : forall (es : chain) (e : event),
  (forall e0, In e0 es -> axiom_valid_event e0) ->
  axiom_valid_event e ->
  forall e0, In e0 (es ++ [e]) -> axiom_valid_event e0.
Proof.
  intros es e Hvalid He e0 Hin. apply in_app_or in Hin.
  destruct Hin as [Hin | Hin]; [apply Hvalid; auto |].
  destruct Hin as [Heq | []]. subst. apply He.
Qed.

(* Helper: appending a larger id preserves distinctness. *)
Lemma distinct_ids_append : forall (es : chain) (e : event),
  distinct_ids es ->
  (forall e', In e' es -> event_id e' < event_id e) ->
  distinct_ids (es ++ [e]).
Proof.
  induction es as [| e' es' IH]; simpl; intros e Hdist Hlt.
  - split; [intros e' Hin; destruct Hin | auto].
  - split.
    + intros e0 Hin. apply in_app_or in Hin. destruct Hin as [Hin | Hin].
      * destruct Hdist as [Hneq _]. apply Hneq. apply Hin.
      * destruct Hin as [Heq | []]. subst. apply Nat.lt_neq. apply Hlt. left. reflexivity.
    + apply IH.
      * destruct Hdist as [_ Hdist]. apply Hdist.
      * intros e0 Hin. apply Hlt. right. apply Hin.
Qed.

(* Helper: appending a larger id preserves increasing ids. *)
Lemma increasing_ids_append : forall (es : chain) (e : event),
  axiom_increasing_ids es ->
  (forall e', In e' es -> event_id e' < event_id e) ->
  axiom_increasing_ids (es ++ [e]).
Proof.
  induction es as [| e1 es' IH]; simpl; intros e Hinc Hlt.
  - auto.
  - destruct es' as [| e2].
    + simpl. split; [apply Hlt; left; reflexivity | auto].
    + destruct Hinc as [Hlt' Hinc]. split; [apply Hlt' |].
      apply IH; [apply Hinc |].
      intros e0 Hin. apply Hlt. right. apply Hin.
Qed.

(* Helper: appending with correct prev preserves linkage. *)
Lemma prev_linkage_aux_append : forall (es : chain) (e : event) (prev_id : option nat),
  es <> nil ->
  prev_linkage_aux es prev_id ->
  prev e = Some (event_id (last es e)) ->
  prev_linkage_aux (es ++ [e]) prev_id.
Proof.
  induction es as [| e1 es' IH]; simpl; intros e prev_id Hneq Hlink Hprev.
  - exfalso. apply Hneq. reflexivity.
  - destruct es' as [| e2 es''].
    + simpl in Hlink. simpl. split;
        [ apply Hlink
        | split; [apply Hprev | auto] ].
    + simpl in Hlink. destruct Hlink as [Hlink1 [Hlink2 Hlink3]]. simpl. split.
      * apply Hlink1.
      * apply IH; [discriminate | split; [apply Hlink2 | apply Hlink3] | apply Hprev].
Qed.

Lemma prev_linkage_append : forall (es : chain) (e : event),
  es <> nil ->
  axiom_prev_linkage es ->
  prev e = Some (event_id (last es e)) ->
  axiom_prev_linkage (es ++ [e]).
Proof.
  intros es e Hneq Hlink Hprev. apply prev_linkage_aux_append; assumption.
Qed.

(* In a non-empty increasing-id chain, every element is <= the last element. *)
Lemma all_ids_le_last : forall (es : chain) (d : event),
  es <> nil ->
  axiom_increasing_ids es ->
  (forall e, In e es -> event_id e <= event_id (last es d)).
Proof.
  induction es as [| e1 es' IH]; simpl; intros d Hneq Hinc e Hin.
  - congruence.
  - destruct Hin as [Heq | Hin].
    + subst e1. destruct es' as [| e2].
      * simpl. lia.
      * simpl in Hinc. destruct Hinc as [Hlt Hinc].
        assert (event_id e2 <= event_id (last (e2 :: es') d)).
        { apply IH; [discriminate | apply Hinc | left; reflexivity]. }
        simpl in H. simpl. lia.
    + destruct es' as [| e2].
      * inversion Hin.
      * simpl in Hinc. destruct Hinc as [_ Hinc].
        apply IH; [discriminate | apply Hinc | apply Hin].
Qed.

(* Theorem T7: appending a valid event preserves well-formedness. *)
Theorem well_formedness_preservation : forall (es : chain) (e : event),
  well_formed es -> valid_append es e -> well_formed (es ++ [e]).
Proof.
  intros es e Hwf Happ.
  destruct Hwf as [Hvalid [Hdist [Hinc [Hprev _]]]].
  assert (Hlt : forall e', In e' es -> event_id e' < event_id e).
  {
    destruct es as [| e0 es0]; [intros e' Hin; inversion Hin|].
    destruct Happ as [Hlt_last _].
    intros e' Hin.
    destruct es0 as [| e1 es1].
    - simpl in Hlt_last. simpl in Hin. destruct Hin as [Heq | []]. subst. lia.
    - assert (Hle : event_id e' <= event_id (last (e0 :: e1 :: es1) e)).
      { apply all_ids_le_last with (d := e); auto. discriminate. }
      lia.
  }
  repeat split.
  - apply (all_events_valid_append es e); [| apply (valid_append_valid_event es e); apply Happ].
    apply Hvalid.
  - apply (distinct_ids_append es e); [apply Hdist | apply Hlt].
  - apply (increasing_ids_append es e); [apply Hinc | apply Hlt].
  - destruct es as [| e0 es0].
    + destruct Happ as [Hprev' _]. simpl. split; [apply Hprev' | auto].
    + apply (prev_linkage_append (e0 :: es0) e).
      * discriminate.
      * apply Hprev.
      * destruct Happ as [_ [Hprev' _]]. apply Hprev'.
  all: auto.
Qed.
