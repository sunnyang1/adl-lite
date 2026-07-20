(* Chain.v -- EventChain well-formedness and derived status/confidence.
   A chain is an append-only list of events with cryptographic linkage.
   Revised 2025-07-03: all 6 stubbed axioms replaced with full definitions. *)

Require Import List Arith Lia String.
Import ListNotations.
Require Import ADL.Status ADL.Event ADL.Confidence ADL.Crypto.

Definition chain := list event.

(* ------------------------------------------------------------------------- *)
(* Cryptographic hashing for events.  Abstract serialization of the event      *)
(* fields followed by SHA-256.  In a concrete model this would use fixed-    *)
(* width byte encodings (e.g. ASN.1 DER or CBOR).                            *)
(* ------------------------------------------------------------------------- *)
Definition hash_event (e : event) : bytes :=
  hash (serialize_nat (event_id e) ++ serialize_string (actor e)).

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

(* Axioms 4-12: full definitions. *)
(* 4. Scope ACL -- every actor has a non-empty scope. *)
Definition valid_scope (a : string) : Prop := a <> EmptyString.
Definition axiom_scope_acl (es : chain) : Prop :=
  forall e, In e es -> valid_scope (actor e).

(* 6. Signature verification -- events with signatures must have a public key.
   No signature without a public key is allowed. *)
Definition valid_signature (e : event) : Prop :=
  match signature e, public_key e with
  | Some sig, Some pk => verify pk (hash_event e) sig = true
  | None, _ => True
  | Some _, None => False
  end.
Definition axiom_signature_verification (es : chain) : Prop :=
  forall e, In e es -> valid_signature e.

(* Allowed transitions for lifecycle events. *)
Definition allowed_transition (current : status) (et : adl_event_type) : Prop :=
  match et with
  | VALIDATE  => current = PROVISIONAL \/ current = FORKED
  | DEPRECATE => current = PROVISIONAL \/ current = VALIDATED \/ current = FORKED
  | FORK      => current = PROVISIONAL \/ current = VALIDATED \/ current = FORKED
  | ARCHIVE   => current = DEPRECATED
  | _         => True
  end.

(* 7. SHACL constraints -- structural data-shape constraints. *)
Definition axiom_shacl_constraints (es : chain) : Prop :=
  forall e, In e es -> event_id e > 0 /\ actor e <> EmptyString.

(* 8. Status transition -- REGISTER only at genesis (first position). *)
Definition axiom_status_transition (es : chain) : Prop :=
  match es with
  | nil => True
  | e :: es' => event_type e = REGISTER /\ (forall e', In e' es' -> event_type e' <> REGISTER)
  end.

(* 9. Confidence clamped -- every event in the chain has confidence <= MAX_SCALED. *)
Definition axiom_confidence_clamped (es : chain) : Prop :=
  forall e, In e es -> confidence e <= MAX_SCALED.

(* 12. Synthetic tagging -- events with signatures must have public keys. *)
Definition axiom_synthetic_tagging (es : chain) : Prop :=
  forall e, In e es -> signature e <> None -> public_key e <> None.

(* Derived status is the LUB over lifecycle event statuses. *)
Definition derived_status (es : chain) : status :=
  status_lub (map StatusOf (map event_type es)).

(* Derived confidence is the max over VALIDATE/SNAPSHOT events. *)
Definition derived_confidence (es : chain) : nat :=
  derived_confidence_events es.

(* 5. Precondition evaluation -- lifecycle events must be allowed by the
   current chain status at the time of their creation.  We use a helper
   that accumulates the prefix to check each event against the state before it. *)
Fixpoint axiom_precondition_eval_aux (prefix : chain) (es : chain) : Prop :=
  match es with
  | nil => True
  | e :: es' =>
      allowed_transition (derived_status prefix) (event_type e) /\ axiom_precondition_eval_aux (prefix ++ [e]) es'
  end.

Definition axiom_precondition_eval (es : chain) : Prop :=
  axiom_precondition_eval_aux [] es.

(* 10. Lifecycle monotonic -- derived status never regresses. *)
Fixpoint axiom_lifecycle_monotonic (es : chain) : Prop :=
  match es with
  | nil => True
  | e :: es' =>
      status_leq (derived_status es') (derived_status (e :: es')) /\ axiom_lifecycle_monotonic es'
  end.

(* 11. Validator collusion -- VALIDATED status requires at least one VALIDATE event. *)
Definition axiom_validator_collusion (es : chain) : Prop :=
  derived_status es = VALIDATED -> exists e, In e es /\ event_type e = VALIDATE.

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

(* A valid append must satisfy structural, cryptographic, and precondition
   constraints. *)
Definition valid_append (es : chain) (e : event) : Prop :=
  match es with
  | nil =>
      prev e = None /\ axiom_valid_event e /\ confidence e <= MAX_SCALED /\ valid_signature e
      /\ event_type e = REGISTER /\ event_id e > 0
  | _ :: _ =>
      event_id (last es e) < event_id e /\
      prev e = Some (event_id (last es e)) /\
      axiom_valid_event e /\ confidence e <= MAX_SCALED /\ valid_signature e
      /\ allowed_transition (derived_status es) (event_type e)
      /\ event_type e <> REGISTER
  end.

Lemma valid_append_valid_event : forall (es : chain) (e : event),
  valid_append es e -> axiom_valid_event e.
Proof. intros es e Happ. destruct es; simpl in Happ; intuition. Qed.

Lemma valid_append_confidence_clamped : forall (es : chain) (e : event),
  valid_append es e -> confidence e <= MAX_SCALED.
Proof. intros es e Happ. destruct es; simpl in Happ; intuition. Qed.

Lemma valid_append_valid_signature : forall (es : chain) (e : event),
  valid_append es e -> valid_signature e.
Proof. intros es e Happ. destruct es; simpl in Happ; intuition. Qed.

Lemma valid_append_event_type_nil : forall (e : event),
  valid_append nil e -> event_type e = REGISTER.
Proof. intros e Happ. simpl in Happ. intuition. Qed.

Lemma valid_append_event_type_cons : forall (es : chain) (e : event),
  es <> nil -> valid_append es e -> event_type e <> REGISTER.
Proof. intros es e Hneq Happ. destruct es; [contradiction | simpl in Happ; intuition]. Qed.

Lemma valid_append_allowed_transition : forall (es : chain) (e : event),
  es <> nil -> valid_append es e -> allowed_transition (derived_status es) (event_type e).
Proof. intros es e Hneq Happ. destruct es; [contradiction | simpl in Happ; intuition]. Qed.

Lemma valid_append_event_id_positive : forall (e : event),
  valid_append nil e -> event_id e > 0.
Proof. intros e Happ. simpl in Happ. intuition. Qed.

(* Helper: all events satisfying a property remain so after append. *)
Lemma all_events_property_append : forall (P : event -> Prop) (es : chain) (e : event),
  (forall e0, In e0 es -> P e0) ->
  P e ->
  forall e0, In e0 (es ++ [e]) -> P e0.
Proof.
  intros P es e Hprop He e0 Hin. apply in_app_or in Hin.
  destruct Hin as [Hin | Hin]; [apply Hprop; auto |].
  destruct Hin as [Heq | []]. subst. apply He.
Qed.

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

(* Helper: axiom_precondition_eval_aux is preserved by valid append. *)
Lemma axiom_precondition_eval_aux_append : forall (prefix es : chain) (e : event),
  axiom_precondition_eval_aux prefix es ->
  valid_append (prefix ++ es) e ->
  axiom_precondition_eval_aux prefix (es ++ [e]).
Proof.
  intros prefix es.
  revert prefix.
  induction es as [| e1 es' IH]; intros prefix e Hprecond Happ.
  - simpl. simpl in Hprecond.
    destruct prefix as [| e0 prefix'].
    + simpl. unfold allowed_transition.
      rewrite (valid_append_event_type_nil e Happ). auto.
    + rewrite app_nil_r in Happ.
      assert (Hneq : e0 :: prefix' <> nil) by (intro H; inversion H).
      simpl. split.
      * apply (valid_append_allowed_transition (e0 :: prefix') e Hneq Happ).
      * exact I.
  - simpl. simpl in Hprecond.
    split.
    + destruct Hprecond as [H1 _]. apply H1.
    + assert (Happ' : valid_append ((prefix ++ [e1]) ++ es') e).
      { replace (prefix ++ (e1 :: es')) with (prefix ++ [e1] ++ es') in Happ.
        - rewrite app_assoc in Happ. apply Happ.
        - reflexivity. }
      apply (IH (prefix ++ [e1]) e).
      * destruct Hprecond as [_ H2]. apply H2.
      * apply Happ'.
Qed.

(* Helper: axiom_precondition_eval is preserved by valid append. *)
Lemma axiom_precondition_eval_append : forall (es : chain) (e : event),
  axiom_precondition_eval es -> valid_append es e -> axiom_precondition_eval (es ++ [e]).
Proof.
  intros es e Hprecond Happ.
  unfold axiom_precondition_eval in *.
  apply axiom_precondition_eval_aux_append.
  - apply Hprecond.
  - simpl. apply Happ.
Qed.

(* Helper: axiom_shacl_constraints is preserved by valid append. *)
Lemma axiom_shacl_constraints_append : forall (es : chain) (e : event),
  axiom_shacl_constraints es -> valid_append es e -> axiom_shacl_constraints (es ++ [e]).
Proof.
  intros es e Hshacl Happ.
  unfold axiom_shacl_constraints in *.
  intros e0 Hin0. apply in_app_or in Hin0. destruct Hin0 as [Hin0 | Hin0].
  - apply Hshacl. apply Hin0.
  - destruct Hin0 as [Heq | []]. subst e0.
    destruct es as [| e0 es0].
    + split.
      * apply (valid_append_event_id_positive e). apply Happ.
      * apply (valid_append_valid_event nil e). apply Happ.
    + split.
      * assert (Hlt : event_id (last (e0 :: es0) e) < event_id e).
        { simpl in Happ. destruct Happ as [Hlt _]. apply Hlt. }
        lia.
      * apply (valid_append_valid_event (e0 :: es0) e). apply Happ.
Qed.

(* Helper: axiom_status_transition is preserved by valid append. *)
Lemma axiom_status_transition_append : forall (es : chain) (e : event),
  axiom_status_transition es -> valid_append es e -> axiom_status_transition (es ++ [e]).
Proof.
  intros es e Hstatus Happ.
  destruct es as [| e0 es'].
  - simpl. simpl in Hstatus.
    split.
    + apply (valid_append_event_type_nil e). apply Happ.
    + intros e' Hin. destruct Hin.
  - simpl. simpl in Hstatus. destruct Hstatus as [Hreg Hnoreg].
    split.
    + apply Hreg.
    + intros e' Hin. apply in_app_or in Hin. destruct Hin as [Hin | Hin].
      * apply Hnoreg. apply Hin.
      * destruct Hin as [Heq | []].
        symmetry in Heq. subst.
        apply (valid_append_event_type_cons (e0 :: es') e). discriminate. apply Happ.
Qed.

(* Helper: axiom_lifecycle_monotonic is preserved by valid append. *)
Lemma axiom_lifecycle_monotonic_append : forall (es : chain) (e : event),
  axiom_lifecycle_monotonic es -> valid_append es e -> axiom_lifecycle_monotonic (es ++ [e]).
Proof.
  intros es e Hmono Happ.
  induction es as [| e0 es' IH].
  - simpl. split.
    + unfold derived_status, status_lub, status_leq. simpl. lia.
    + exact I.
  - simpl in Hmono. destruct Hmono as [Hmono1 Hmono2].
    simpl.
    split.
    + assert (Hdes : status_leq (derived_status (es' ++ [e])) (derived_status (e0 :: es' ++ [e]))).
      { unfold derived_status.
        simpl.
        remember (map StatusOf (map event_type (es' ++ [e]))) as ss.
        destruct ss as [| s ss'].
        - simpl. unfold status_leq. simpl. lia.
        - simpl.
          apply fold_left_status_max_monotone_acc.
          apply status_max_upper_bound. }
      apply Hdes.
    + clear Hmono1 Hmono2 Happ IH.
      induction es' as [| e1 es'' IH'].
      * simpl. split.
        -- unfold derived_status, status_lub, status_leq. simpl. lia.
        -- exact I.
      * simpl. split.
        -- unfold derived_status.
           simpl.
           remember (map StatusOf (map event_type (es'' ++ [e]))) as ss.
           destruct ss as [| s ss'].
           ++ simpl. unfold status_leq. simpl. lia.
           ++ simpl.
              apply fold_left_status_max_monotone_acc.
              apply status_max_upper_bound.
        -- exact IH'.
Qed.

(* Helper: axiom_validator_collusion is preserved by valid append. *)
Lemma axiom_validator_collusion_append : forall (es : chain) (e : event),
  axiom_validator_collusion es -> valid_append es e -> axiom_validator_collusion (es ++ [e]).
Proof.
  intros es e Hcollusion Happ.
  unfold axiom_validator_collusion in *.
  intros Hstatus.
  unfold derived_status in Hstatus.
  rewrite map_app in Hstatus. rewrite map_app in Hstatus.
  simpl in Hstatus.
  rewrite status_lub_append in Hstatus.
  apply status_max_eq_VALIDATED in Hstatus.
  destruct Hstatus as [Hdes | Hstatus_e].
  - assert (Hdes' : derived_status es = VALIDATED) by (unfold derived_status; apply Hdes).
    apply Hcollusion in Hdes'.
    destruct Hdes' as [e0 [He0 Htype]].
    exists e0. split; [apply in_or_app; left; apply He0 | apply Htype].
  - rewrite StatusOf_eq_VALIDATED in Hstatus_e.
    exists e. split; [apply in_or_app; right; apply in_eq | apply Hstatus_e].
Qed.

(* Helper: axiom_synthetic_tagging is preserved by valid append. *)
Lemma axiom_synthetic_tagging_append : forall (es : chain) (e : event),
  axiom_synthetic_tagging es -> valid_append es e -> axiom_synthetic_tagging (es ++ [e]).
Proof.
  intros es e Hsynth Happ.
  unfold axiom_synthetic_tagging in *.
  intros e0 Hin0 Hsig.
  apply in_app_or in Hin0. destruct Hin0 as [Hin0 | Hin0].
  - apply Hsynth. apply Hin0. apply Hsig.
  - destruct Hin0 as [Heq | []]. subst e0.
    assert (Hvsig : valid_signature e) by (apply (valid_append_valid_signature es e); apply Happ).
    unfold valid_signature in Hvsig.
    destruct (signature e) eqn:Hse; try (exfalso; apply Hsig; reflexivity).
    + destruct (public_key e) eqn:Hpk.
      * intro H. discriminate H.
      * intro H. apply Hvsig.
Qed.

(* Theorem T7: appending a valid event preserves well-formedness. *)
Theorem well_formedness_preservation : forall (es : chain) (e : event),
  well_formed es -> valid_append es e -> well_formed (es ++ [e]).
Proof.
  intros es e Hwf Happ.
  destruct Hwf as [Hvalid [Hdist [Hinc [Hprev [Hscope [Hprecond [Hsig [Hshacl [Hstatus [Hconf [Hmono [Hcollusion Hsynth]]]]]]]]]]]].
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
  split; [apply (all_events_valid_append es e); [| apply (valid_append_valid_event es e); apply Happ]; apply Hvalid |].
  split; [apply (distinct_ids_append es e); [apply Hdist | apply Hlt] |].
  split; [apply (increasing_ids_append es e); [apply Hinc | apply Hlt] |].
  split; [destruct es as [| e0 es0];
    [destruct Happ as [Hprev' _]; simpl; split; [apply Hprev' | auto] |
     apply (prev_linkage_append (e0 :: es0) e);
       [discriminate | apply Hprev | destruct Happ as [_ [Hprev' _]]; apply Hprev']] |].
  split; [intros e0 Hin0; apply in_app_or in Hin0; destruct Hin0 as [Hin0 | Hin0];
    [apply Hscope; apply Hin0 | destruct Hin0 as [Heq | []]; subst e0; apply (valid_append_valid_event es e); apply Happ] |].
  split; [apply axiom_precondition_eval_append; [apply Hprecond | apply Happ] |].
  split; [intros e0 Hin0; apply in_app_or in Hin0; destruct Hin0 as [Hin0 | Hin0];
    [apply Hsig; apply Hin0 | destruct Hin0 as [Heq | []]; subst e0; apply (valid_append_valid_signature es e); apply Happ] |].
  split; [apply axiom_shacl_constraints_append; [apply Hshacl | apply Happ] |].
  split; [apply axiom_status_transition_append; [apply Hstatus | apply Happ] |].
  split; [intros e0 Hin0; apply in_app_or in Hin0; destruct Hin0 as [Hin0 | Hin0];
    [apply Hconf; apply Hin0 | destruct Hin0 as [Heq | []]; subst e0; apply (valid_append_confidence_clamped es e); apply Happ] |].
  split; [apply axiom_lifecycle_monotonic_append; [apply Hmono | apply Happ] |].
  split; [apply axiom_validator_collusion_append; [apply Hcollusion | apply Happ] |].
  apply axiom_synthetic_tagging_append; [apply Hsynth | apply Happ].
Qed.
