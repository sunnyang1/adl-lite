(* CRDT.v -- branch merge semantics for EventChain.
   Merge is commutative, associative, idempotent, and preserves well-formedness.
   This file provides a closed proof skeleton for those properties.  The CRDT
   algebraic identities are reduced to a normalized-id set view; event-level
   equality is then obtained via an event-content equivalence that ignores the
   mutable [prev] field (the final [reanchor] overwrites [prev] anyway). *)

Require Import List Arith Bool String Lia.
Require Import Coq.Sorting.Permutation Coq.Sorting.Sorted.
Import ListNotations.
Require Import ADL.Event ADL.Chain.

Definition branch := chain.

(* ------------------------------------------------------------------------- *)
(* Decidable event equality.                                                 *)
(* ------------------------------------------------------------------------- *)

Lemma adl_event_type_eq_dec : forall x y : adl_event_type, {x = y} + {x <> y}.
Proof. decide equality. Defined.

Lemma option_eq_dec {A} (dec : forall x y : A, {x = y} + {x <> y}) :
  forall o1 o2 : option A, {o1 = o2} + {o1 <> o2}.
Proof. decide equality. Defined.

Lemma event_eq_dec : forall e1 e2 : event, {e1 = e2} + {e1 <> e2}.
Proof.
  intros [i1 a1 t1 c1 p1] [i2 a2 t2 c2 p2].
  destruct (Nat.eq_dec i1 i2); [ | right; congruence ].
  destruct (string_dec a1 a2); [ | right; congruence ].
  destruct (adl_event_type_eq_dec t1 t2); [ | right; congruence ].
  destruct (Nat.eq_dec c1 c2); [ | right; congruence ].
  destruct (option_eq_dec Nat.eq_dec p1 p2); [ | right; congruence ].
  left. f_equal; auto.
Qed.

(* ------------------------------------------------------------------------- *)
(* Event content: the fields that survive a [reanchor].                      *)
(* ------------------------------------------------------------------------- *)

Definition event_content (e : event) : nat * string * adl_event_type * nat :=
  (event_id e, actor e, event_type e, confidence e).

Definition event_content_eq (e1 e2 : event) : Prop :=
  event_content e1 = event_content e2.

Lemma event_content_eq_iff : forall e1 e2,
  event_content_eq e1 e2 <->
    event_id e1 = event_id e2 /\ actor e1 = actor e2 /\ event_type e1 = event_type e2 /\ confidence e1 = confidence e2.
Proof.
  intros e1 e2. unfold event_content_eq, event_content. split.
  - intros Heq. injection Heq. auto.
  - intros [Hid [Ha [Ht Hc]]]. rewrite Hid, Ha, Ht, Hc. reflexivity.
Qed.

Lemma event_content_eq_id : forall e1 e2,
  event_content_eq e1 e2 -> event_id e1 = event_id e2.
Proof. intros e1 e2 Hc. apply event_content_eq_iff in Hc. intuition. Qed.

(* ------------------------------------------------------------------------- *)
(* Cross-branch compatibility: shared IDs refer to the same event.           *)
(* This is the CRDT precondition that makes merge order-independent.         *)
(* ------------------------------------------------------------------------- *)

Definition branch_compat (b1 b2 : branch) : Prop :=
  forall e1 e2, In e1 b1 -> In e2 b2 -> event_id e1 = event_id e2 -> e1 = e2.

Definition branches_compat3 (b1 b2 b3 : branch) : Prop :=
  branch_compat b1 b2 /\ branch_compat b2 b3 /\ branch_compat b1 b3.

Lemma branch_compat_sym : forall b1 b2,
  branch_compat b1 b2 -> branch_compat b2 b1.
Proof.
  intros b1 b2 H e1 e2 Hin1 Hin2 Heq. symmetry. apply H; auto.
Qed.

Lemma distinct_ids_injective : forall es,
  distinct_ids es ->
  forall e1 e2, In e1 es -> In e2 es -> event_id e1 = event_id e2 -> e1 = e2.
Proof.
  induction es as [|e es' IH]; simpl; intros Hdist e1 e2 Hin1 Hin2 Heq.
  - inversion Hin1.
  - destruct Hdist as [Hneq Hdist'].
    apply in_inv in Hin1; apply in_inv in Hin2.
    destruct Hin1 as [He1 | Hin1]; destruct Hin2 as [He2 | Hin2].
    + subst. reflexivity.
    + subst. exfalso. apply (Hneq e2); auto.
    + subst. exfalso. apply (Hneq e1); auto.
    + apply IH; auto.
Qed.

Lemma wf_distinct : forall es, well_formed es -> distinct_ids es.
Proof. intros es Hwf. destruct Hwf as [_ [Hdist _]]. apply Hdist. Qed.

Lemma branch_compat_self : forall b,
  well_formed b -> branch_compat b b.
Proof.
  intros b Hwf e1 e2 Hin1 Hin2 Heq.
  apply (distinct_ids_injective b); auto. apply wf_distinct; auto.
Qed.

Lemma all_same_id_equal_in_union : forall b1 b2,
  well_formed b1 -> well_formed b2 -> branch_compat b1 b2 ->
  forall e1 e2, In e1 (b1 ++ b2) -> In e2 (b1 ++ b2) ->
    event_id e1 = event_id e2 -> e1 = e2.
Proof.
  intros * Hwf1 Hwf2 Hcompat e1 e2 Hin1 Hin2 Heq.
  apply in_app_or in Hin1; apply in_app_or in Hin2.
  destruct Hin1 as [Hin1 | Hin1]; destruct Hin2 as [Hin2 | Hin2].
  - apply (distinct_ids_injective b1); auto. apply wf_distinct; auto.
  - apply Hcompat; auto.
  - symmetry. apply Hcompat; auto.
  - apply (distinct_ids_injective b2); auto. apply wf_distinct; auto.
Qed.

Lemma in_app3_or : forall {A} (b1 b2 b3 : list A) e,
  In e (b1 ++ b2 ++ b3) <-> In e b1 \/ In e b2 \/ In e b3.
Proof. intros. rewrite !in_app_iff. tauto. Qed.

Lemma all_same_id_equal_in_union3 : forall b1 b2 b3,
  well_formed b1 -> well_formed b2 -> well_formed b3 ->
  branches_compat3 b1 b2 b3 ->
  forall e1 e2, In e1 (b1 ++ b2 ++ b3) -> In e2 (b1 ++ b2 ++ b3) ->
    event_id e1 = event_id e2 -> e1 = e2.
Proof.
  intros * Hwf1 Hwf2 Hwf3 Hcompat e1 e2 Hin1 Hin2 Heq.
  destruct Hcompat as [H12 [H23 H13]].
  rewrite in_app3_or in Hin1. destruct Hin1 as [H1 | [H2 | H3]].
  - rewrite in_app3_or in Hin2. destruct Hin2 as [H1' | [H2' | H3']].
    + apply (distinct_ids_injective b1); auto; apply wf_distinct; auto.
    + apply H12; auto.
    + apply H13; auto.
  - rewrite in_app3_or in Hin2. destruct Hin2 as [H1' | [H2' | H3']].
    + symmetry. apply H12; auto.
    + apply (distinct_ids_injective b2); auto; apply wf_distinct; auto.
    + apply H23; auto.
  - rewrite in_app3_or in Hin2. destruct Hin2 as [H1' | [H2' | H3']].
    + symmetry. apply H13; auto.
    + symmetry. apply H23; auto.
    + apply (distinct_ids_injective b3); auto; apply wf_distinct; auto.
Qed.

(* ------------------------------------------------------------------------- *)
(* Insertion sort / deduplication on event IDs.                              *)
(* ------------------------------------------------------------------------- *)

Definition ids_of (es : chain) : list nat := map event_id es.

Fixpoint insert_nat (n : nat) (ns : list nat) : list nat :=
  match ns with
  | nil => n :: nil
  | m :: ns' =>
      if Nat.leb n m then n :: m :: ns' else m :: insert_nat n ns'
  end.

Fixpoint sort_nat (ns : list nat) : list nat :=
  match ns with
  | nil => nil
  | n :: ns' => insert_nat n (sort_nat ns')
  end.

Fixpoint dedup_nat (ns : list nat) : list nat :=
  match ns with
  | nil => nil
  | n :: ns' =>
      if existsb (Nat.eqb n) ns' then dedup_nat ns' else n :: dedup_nat ns'
  end.

Definition normalized_ids (ns : list nat) : list nat := sort_nat (dedup_nat ns).

Lemma existsb_eq_in : forall n ns,
  existsb (Nat.eqb n) ns = true <-> exists m, In m ns /\ n = m.
Proof.
  intros n ns. rewrite existsb_exists. split; intros [x [Hin Heq]].
  - exists x. split; auto. apply Nat.eqb_eq in Heq. lia.
  - exists x. split; auto. apply Nat.eqb_eq. lia.
Qed.

Lemma existsb_eq_in_false : forall n ns,
  existsb (Nat.eqb n) ns = false <-> ~ (exists m, In m ns /\ n = m).
Proof.
  intros n ns. split.
  - intros H [m [Hin Heq]].
    assert (Hex : existsb (Nat.eqb n) ns = true).
    { apply existsb_eq_in. exists m. split; auto. }
    subst n. rewrite Hex in H. discriminate.
  - intros H. destruct (existsb (Nat.eqb n) ns) eqn:E; auto.
    apply existsb_eq_in in E. exfalso. apply H. eauto.
Qed.

Lemma insert_nat_perm : forall n ns,
  Permutation (insert_nat n ns) (n :: ns).
Proof.
  induction ns as [|m ns' IH]; simpl.
  - apply Permutation_refl.
  - destruct (Nat.leb n m) eqn:Hle.
    + apply Permutation_refl.
    + replace (insert_nat n (m :: ns')) with (m :: insert_nat n ns').
      * apply (perm_trans (l':= m :: n :: ns')).
        -- apply perm_skip. apply IH.
        -- apply perm_swap.
      * simpl. rewrite Hle. reflexivity.
Qed.

Lemma sort_nat_perm : forall ns, Permutation (sort_nat ns) ns.
Proof.
  induction ns as [|n ns' IH]; simpl.
  - apply Permutation_refl.
  - apply (perm_trans (l':= n :: sort_nat ns')).
    + apply insert_nat_perm.
    + apply perm_skip. apply IH.
Qed.

Lemma dedup_nat_in : forall n ns, In n (dedup_nat ns) <-> In n ns.
Proof.
  intros n ns. revert n. induction ns as [|m ns' IH]; simpl; intros n.
  - split; auto.
  - destruct (existsb (Nat.eqb m) ns') eqn:Hex.
    + split.
      * intros Hin. apply IH in Hin. right. apply Hin.
      * intros Hin. destruct Hin as [Heq | Hin].
        -- subst n. apply existsb_eq_in in Hex.
           destruct Hex as [x [Hin' Heq']].
           rewrite Heq'. apply IH. apply Hin'.
        -- apply IH. apply Hin.
    + split.
      * intros Hin. destruct Hin as [Heq | Hin];
          [left; auto | right; apply IH; apply Hin].
      * intros Hin. destruct Hin as [Heq | Hin];
          [left; auto | right; apply IH; apply Hin].
Qed.

Lemma dedup_nat_nodup : forall ns, NoDup (dedup_nat ns).
Proof.
  induction ns as [|n ns' IH]; simpl.
  - constructor.
  - destruct (existsb (Nat.eqb n) ns') eqn:Hex.
    + apply IH.
    + constructor; [| apply IH].
      intro Hin. rewrite (dedup_nat_in n ns') in Hin.
      apply existsb_eq_in_false in Hex. exfalso. apply Hex.
      exists n. split; [assumption | reflexivity].
Qed.

Lemma perm_in_iff {A} (l l' : list A) :
  Permutation l l' -> forall a, In a l <-> In a l'.
Proof.
  intros Hp a. split; apply Permutation_in; auto using Permutation_sym.
Qed.

Lemma normalized_ids_in : forall n ns,
  In n (normalized_ids ns) <-> In n ns.
Proof.
  intros n ns. unfold normalized_ids. split.
  - intros Hin. apply (Permutation_in n (sort_nat_perm (dedup_nat ns))) in Hin.
    apply dedup_nat_in. apply Hin.
  - intros Hin. apply (Permutation_in n (Permutation_sym (sort_nat_perm (dedup_nat ns)))).
    apply dedup_nat_in. apply Hin.
Qed.

Lemma normalized_ids_nodup : forall ns, NoDup (normalized_ids ns).
Proof.
  intros ns. apply Permutation_NoDup with (dedup_nat ns).
  - apply Permutation_sym. apply sort_nat_perm.
  - apply dedup_nat_nodup.
Qed.

(* Insertion sort produces a [<=]-sorted list. *)

Lemma HdRel_insert : forall n m ns,
  m <= n -> HdRel le m ns -> HdRel le m (insert_nat n ns).
Proof.
  induction ns as [|k ns' IH]; simpl; intros Hmn Hhd.
  - apply HdRel_cons. exact Hmn.
  - destruct (Nat.leb n k) eqn:Hle.
    + apply HdRel_cons. exact Hmn.
    + inversion Hhd; subst. apply HdRel_cons. auto.
Qed.

Lemma insert_nat_sorted : forall n ns,
  Sorted le ns -> Sorted le (insert_nat n ns).
Proof.
  induction ns as [|m ns' IH]; intros Hsorted.
  - repeat constructor.
  - simpl. destruct (Nat.leb n m) eqn:Hle.
    + constructor.
      * apply Hsorted.
      * apply HdRel_cons. apply Nat.leb_le. auto.
    + inversion Hsorted as [ | ? ? Hsorted' Hhd ]; subst.
      constructor.
      * apply IH. apply Hsorted'.
      * apply HdRel_insert. apply Nat.leb_nle in Hle. lia. apply Hhd.
Qed.

Lemma sort_nat_sorted : forall ns, Sorted le (sort_nat ns).
Proof.
  induction ns as [|n ns' IH]; simpl.
  - constructor.
  - apply insert_nat_sorted. apply IH.
Qed.

Lemma normalized_ids_sorted : forall ns, Sorted le (normalized_ids ns).
Proof. intros. apply sort_nat_sorted. Qed.

(* Sorted lists with the same elements are equal. *)
Lemma sorted_perm_eq : forall l1 l2,
  Sorted le l1 -> Sorted le l2 -> Permutation l1 l2 -> l1 = l2.
Proof.
  induction l1 as [|a l1' IH]; intros [|b l2'] Hs1 Hs2 Hp.
  - reflexivity.
  - apply Permutation_nil in Hp. discriminate.
  - apply Permutation_sym in Hp. apply Permutation_nil in Hp. discriminate.
  - assert (Ha : forall x, In x l1' -> a <= x).
    { apply Forall_forall. apply (Sorted_extends Nat.le_trans Hs1). }
    assert (Hb : forall x, In x l2' -> b <= x).
    { apply Forall_forall. apply (Sorted_extends Nat.le_trans Hs2). }
    assert (Ina : In a (b :: l2'))
      by (apply (@Permutation_in nat (a :: l1') (b :: l2') a Hp); left; auto).
    assert (Inb : In b (a :: l1'))
      by (apply (@Permutation_in nat (b :: l2') (a :: l1') b (Permutation_sym Hp)); left; auto).
    assert (Hab : a = b).
    { destruct Ina as [Heq | Hin]; [auto |].
      destruct Inb as [Heq' | Hin']; [auto |].
      apply Nat.le_antisymm; [apply Ha | apply Hb]; auto. }
    subst b. f_equal. apply IH.
    + inversion Hs1; auto.
    + inversion Hs2; auto.
    + apply Permutation_cons_inv with (a := a). apply Hp.
Qed.

Lemma normalized_ids_eq_iff : forall ns1 ns2,
  normalized_ids ns1 = normalized_ids ns2 <-> (forall n, In n ns1 <-> In n ns2).
Proof.
  intros ns1 ns2. split.
  - intros Heq n.
    rewrite <- (normalized_ids_in n ns1).
    rewrite <- (normalized_ids_in n ns2).
    rewrite Heq. reflexivity.
  - intros Hin_eq. apply sorted_perm_eq.
    + apply normalized_ids_sorted.
    + apply normalized_ids_sorted.
    + apply NoDup_Permutation.
      * apply normalized_ids_nodup.
      * apply normalized_ids_nodup.
      * intros n. rewrite !normalized_ids_in. apply Hin_eq.
Qed.

Lemma normalized_ids_app_l : forall xs ys,
  normalized_ids (xs ++ normalized_ids ys) = normalized_ids (xs ++ ys).
Proof.
  intros xs ys. apply normalized_ids_eq_iff. intros n.
  rewrite !in_app_iff, normalized_ids_in. reflexivity.
Qed.

Lemma normalized_ids_app_r : forall xs ys,
  normalized_ids (normalized_ids xs ++ ys) = normalized_ids (xs ++ ys).
Proof.
  intros xs ys. apply normalized_ids_eq_iff. intros n.
  rewrite !in_app_iff, normalized_ids_in. reflexivity.
Qed.

(* Unfolded variants for goals where [normalized_ids] has been expanded.       *)
Lemma sort_dedup_app_l : forall xs ys,
  sort_nat (dedup_nat (xs ++ sort_nat (dedup_nat ys))) =
  sort_nat (dedup_nat (xs ++ ys)).
Proof.
  intros xs ys. apply normalized_ids_eq_iff. intros n.
  rewrite !in_app_iff.
  replace (sort_nat (dedup_nat ys)) with (normalized_ids ys) by reflexivity.
  rewrite normalized_ids_in. reflexivity.
Qed.

Lemma sort_dedup_app_r : forall xs ys,
  sort_nat (dedup_nat (sort_nat (dedup_nat xs) ++ ys)) =
  sort_nat (dedup_nat (xs ++ ys)).
Proof.
  intros xs ys. apply normalized_ids_eq_iff. intros n.
  rewrite !in_app_iff.
  replace (sort_nat (dedup_nat xs)) with (normalized_ids xs) by reflexivity.
  rewrite normalized_ids_in. reflexivity.
Qed.

(* ------------------------------------------------------------------------- *)
(* Merge definitions.                                                        *)
(* ------------------------------------------------------------------------- *)

Fixpoint insert_by_id (e : event) (es : branch) : branch :=
  match es with
  | nil => e :: nil
  | e' :: es' =>
      if Nat.leb (event_id e) (event_id e')
      then e :: e' :: es'
      else e' :: insert_by_id e es'
  end.

Fixpoint sort_by_id (es : branch) : branch :=
  match es with
  | nil => nil
  | e :: es' => insert_by_id e (sort_by_id es')
  end.

Fixpoint dedup (es : branch) : branch :=
  match es with
  | nil => nil
  | e :: es' =>
      if existsb (fun e' => Nat.eqb (event_id e) (event_id e')) es'
      then dedup es'
      else e :: dedup es'
  end.

Fixpoint reanchor_aux (es : branch) (prev_id : option nat) : branch :=
  match es with
  | nil => nil
  | e :: es' =>
      mkEvent (event_id e) (actor e) (event_type e) (confidence e) prev_id
      :: reanchor_aux es' (Some (event_id e))
  end.

Definition reanchor (es : branch) : branch := reanchor_aux es None.

Definition merge_branch (b1 b2 : branch) : branch :=
  reanchor (sort_by_id (dedup (b1 ++ b2))).

(* ------------------------------------------------------------------------- *)
(* Membership and ID-preservation facts for the event-level list functions.  *)
(* ------------------------------------------------------------------------- *)

Lemma insert_by_id_in : forall e e0 es,
  In e (insert_by_id e0 es) <-> e = e0 \/ In e es.
Proof.
  induction es as [|e1 es' IH]; simpl.
  - split; intros H; destruct H; auto; contradiction.
  - destruct (Nat.leb (event_id e0) (event_id e1)) eqn:Hle; simpl.
    + split; intros [Heq | Hin]; auto; destruct Hin; auto.
    + rewrite IH. split; intros [Heq | [Heq | Hin]]; auto.
Qed.

Lemma in_sort_by_id : forall e es, In e (sort_by_id es) <-> In e es.
Proof.
  induction es as [|e0 es' IH]; simpl.
  - split; auto.
  - rewrite insert_by_id_in, IH. split; intros [Heq | Hin]; auto.
Qed.

Lemma in_dedup : forall e es, In e (dedup es) -> In e es.
Proof.
  induction es as [|e0 es' IH]; simpl.
  - auto.
  - destruct (existsb (fun e' => Nat.eqb (event_id e0) (event_id e')) es') eqn:Hex.
    + intros Hin. right. apply IH. apply Hin.
    + intros [Heq | Hin]. left. auto. right. apply IH. apply Hin.
Qed.

Lemma existsb_event_id_eq : forall e es,
  existsb (fun e' => Nat.eqb (event_id e) (event_id e')) es
  = existsb (Nat.eqb (event_id e)) (ids_of es).
Proof.
  intros e es. unfold ids_of. induction es as [|e0 es' IH]; simpl.
  - reflexivity.
  - rewrite IH. reflexivity.
Qed.

Lemma insert_by_id_preserves_ids : forall e es,
  ids_of (insert_by_id e es) = insert_nat (event_id e) (ids_of es).
Proof.
  induction es as [|e' es' IH]; simpl.
  - reflexivity.
  - destruct (Nat.leb (event_id e) (event_id e')) eqn:Hle; simpl.
    + reflexivity.
    + simpl. rewrite IH. reflexivity.
Qed.

Lemma sort_by_id_preserves_ids : forall es,
  ids_of (sort_by_id es) = sort_nat (ids_of es).
Proof.
  induction es as [|e es' IH]; simpl.
  - reflexivity.
  - rewrite insert_by_id_preserves_ids, IH. reflexivity.
Qed.

Lemma dedup_preserves_ids : forall es,
  ids_of (dedup es) = dedup_nat (ids_of es).
Proof.
  induction es as [|e es' IH]; simpl.
  - reflexivity.
  - rewrite existsb_event_id_eq.
    destruct (existsb (Nat.eqb (event_id e)) (ids_of es')) eqn:Hex.
    + rewrite IH. reflexivity.
    + simpl. rewrite IH. reflexivity.
Qed.

Lemma reanchor_aux_preserves_ids : forall es prev_id,
  ids_of (reanchor_aux es prev_id) = ids_of es.
Proof.
  induction es as [|e es' IH]; intros prev_id; simpl.
  - reflexivity.
  - rewrite IH. reflexivity.
Qed.

Lemma reanchor_preserves_ids : forall es,
  ids_of (reanchor es) = ids_of es.
Proof.
  intros es. unfold reanchor. apply reanchor_aux_preserves_ids.
Qed.

Lemma ids_of_app : forall b1 b2, ids_of (b1 ++ b2) = ids_of b1 ++ ids_of b2.
Proof. intros. unfold ids_of. apply map_app. Qed.

Lemma merge_branch_ids : forall b1 b2,
  ids_of (merge_branch b1 b2) = normalized_ids (ids_of b1 ++ ids_of b2).
Proof.
  intros b1 b2. unfold merge_branch, normalized_ids, ids_of.
  rewrite reanchor_preserves_ids.
  rewrite sort_by_id_preserves_ids, dedup_preserves_ids.
  rewrite ids_of_app. reflexivity.
Qed.

Lemma ids_merge_comm : forall b1 b2,
  ids_of (merge_branch b1 b2) = ids_of (merge_branch b2 b1).
Proof.
  intros b1 b2. rewrite !merge_branch_ids.
  apply normalized_ids_eq_iff. intros n. rewrite !in_app_iff. firstorder.
Qed.

Lemma ids_merge_assoc : forall b1 b2 b3,
  ids_of (merge_branch b1 (merge_branch b2 b3)) =
  ids_of (merge_branch (merge_branch b1 b2) b3).
Proof.
  intros b1 b2 b3. rewrite !merge_branch_ids.
  rewrite normalized_ids_app_l.
  rewrite normalized_ids_app_r.
  apply normalized_ids_eq_iff. intros n. rewrite !in_app_iff. firstorder.
Qed.

Lemma ids_merge_idem : forall b,
  ids_of (merge_branch b b) = ids_of (merge_branch b nil).
Proof.
  intros b. rewrite !merge_branch_ids. simpl.
  apply normalized_ids_eq_iff. intros n. rewrite !in_app_iff. firstorder.
Qed.

(* ------------------------------------------------------------------------- *)
(* Content-based lifting: [reanchor] only depends on event content.          *)
(* ------------------------------------------------------------------------- *)

Lemma in_reanchor_aux_source_content : forall es prev_id e,
  In e (reanchor_aux es prev_id) ->
  exists s, In s es /\ event_content_eq e s.
Proof.
  induction es as [|e0 es' IH]; simpl; intros prev_id e Hin.
  - destruct Hin.
  - destruct Hin as [Heq | Hin].
    + exists e0. split; [left; auto |].
      subst e. apply event_content_eq_iff. simpl. auto.
    + apply IH in Hin as [s [Hins Hc]]. exists s. split; [right; auto | auto].
Qed.

Lemma in_merge_branch_source_content : forall b1 b2 e,
  In e (merge_branch b1 b2) ->
  exists s, In s (b1 ++ b2) /\ event_content_eq e s.
Proof.
  intros b1 b2 e Hin.
  unfold merge_branch in Hin.
  apply in_reanchor_aux_source_content in Hin as [s [Hins Hc]].
  rewrite in_sort_by_id in Hins. apply in_dedup in Hins.
  exists s. split; auto.
Qed.

Lemma reanchor_aux_eq : forall es1 es2 prev_id,
  Forall2 event_content_eq es1 es2 ->
  reanchor_aux es1 prev_id = reanchor_aux es2 prev_id.
Proof.
  induction es1 as [|e1 es1' IH]; intros es2 prev_id Hf;
    inversion Hf as [ | ? ? ? ? Hhd Htl ]; subst; simpl.
  - reflexivity.
  - f_equal.
    + apply event_content_eq_iff in Hhd as [Hid [Ha [Ht Hc]]].
      f_equal; auto.
    + apply event_content_eq_iff in Hhd as [Hid [Ha [Ht Hc]]].
      rewrite Hid. apply IH. apply Htl.
Qed.

(* If two distinct-id lists have the same IDs and agree on content per ID,
   they are pointwise content-equal. *)
Lemma eq_list_by_content : forall l1 l2,
  ids_of l1 = ids_of l2 ->
  distinct_ids l1 -> distinct_ids l2 ->
  (forall e1 e2, In e1 l1 -> In e2 l2 -> event_id e1 = event_id e2 -> event_content_eq e1 e2) ->
  Forall2 event_content_eq l1 l2.
Proof.
  induction l1 as [|e1 es1 IH]; intros [|e2 es2] Hids Hd1 Hd2 Heq; simpl in *; try discriminate.
  - constructor.
  - injection Hids as Hid Hids'.
    constructor.
    + apply Heq; [left; auto | left; auto | auto].
    + apply IH.
      * apply Hids'.
      * inversion Hd1; auto.
      * inversion Hd2; auto.
      * intros e1' e2' Hin1 Hin2 Hid'. apply Heq; [right; auto | right; auto | auto].
Qed.

(* ------------------------------------------------------------------------- *)
(* The sorted/deduped event sequences are equal up to content under the       *)
(* CRDT compatibility assumptions.                                            *)
(* ------------------------------------------------------------------------- *)

Lemma distinct_ids_NoDup_ids_of : forall es, NoDup (ids_of es) -> distinct_ids es.
Proof.
  induction es as [|e es' IH]; simpl; intros Hnodup.
  - auto.
  - simpl in Hnodup. inversion Hnodup as [ | ? ? Hin Hnodup' ]; subst.
    split.
    + intros e' Hin' Heq. apply Hin. rewrite Heq. apply in_map. apply Hin'.
    + apply IH. apply Hnodup'.
Qed.

Lemma distinct_ids_sort_dedup : forall es, distinct_ids (sort_by_id (dedup es)).
Proof.
  intros es. apply distinct_ids_NoDup_ids_of.
  rewrite sort_by_id_preserves_ids, dedup_preserves_ids.
  apply Permutation_NoDup with (dedup_nat (ids_of es)).
  - apply Permutation_sym. apply sort_nat_perm.
  - apply dedup_nat_nodup.
Qed.

Lemma sort_dedup_content_eq_comm : forall b1 b2,
  well_formed b1 -> well_formed b2 -> branch_compat b1 b2 ->
  Forall2 event_content_eq
    (sort_by_id (dedup (b1 ++ b2)))
    (sort_by_id (dedup (b2 ++ b1))).
Proof.
  intros b1 b2 Hwf1 Hwf2 Hcompat.
  apply eq_list_by_content.
  - rewrite !sort_by_id_preserves_ids, !dedup_preserves_ids, !ids_of_app.
    apply normalized_ids_eq_iff. intros n. rewrite !in_app_iff. firstorder.
  - apply distinct_ids_sort_dedup.
  - apply distinct_ids_sort_dedup.
  - intros e1 e2 Hin1 Hin2 Heq.
    rewrite in_sort_by_id in Hin1. apply in_dedup in Hin1.
    rewrite in_sort_by_id in Hin2. apply in_dedup in Hin2.
    assert (Hin2' : In e2 (b1 ++ b2)) by (apply in_app_or in Hin2; rewrite in_app_iff; tauto).
    assert (e1 = e2).
    { apply (all_same_id_equal_in_union b1 b2); auto. }
    subst. reflexivity.
Qed.

Lemma sort_dedup_content_eq_assoc : forall b1 b2 b3,
  well_formed b1 -> well_formed b2 -> well_formed b3 ->
  branches_compat3 b1 b2 b3 ->
  Forall2 event_content_eq
    (sort_by_id (dedup (b1 ++ merge_branch b2 b3)))
    (sort_by_id (dedup (merge_branch b1 b2 ++ b3))).
Proof.
  intros b1 b2 b3 Hwf1 Hwf2 Hwf3 Hcompat.
  apply eq_list_by_content.
  - rewrite !sort_by_id_preserves_ids, !dedup_preserves_ids, !ids_of_app, !merge_branch_ids.
    unfold normalized_ids.
    rewrite (sort_dedup_app_l (ids_of b1) (ids_of b2 ++ ids_of b3)).
    rewrite (sort_dedup_app_r (ids_of b1 ++ ids_of b2) (ids_of b3)).
    rewrite <- app_assoc. reflexivity.
  - apply distinct_ids_sort_dedup.
  - apply distinct_ids_sort_dedup.
  - intros e1 e2 Hin1 Hin2 Heq.
    rewrite in_sort_by_id in Hin1. apply in_dedup in Hin1.
    rewrite in_sort_by_id in Hin2. apply in_dedup in Hin2.
    assert (Hsrc1 : exists s, In s (b1 ++ b2 ++ b3) /\ event_content_eq e1 s).
    { apply in_app_or in Hin1. destruct Hin1 as [Hin1 | Hin1].
      - exists e1. split; [rewrite in_app_iff; auto | reflexivity].
      - apply in_merge_branch_source_content in Hin1 as [s [Hins Hc]].
        rewrite in_app_iff in Hins.
        exists s. split; [ | apply Hc]. rewrite !in_app_iff. tauto. }
    assert (Hsrc2 : exists s, In s (b1 ++ b2 ++ b3) /\ event_content_eq e2 s).
    { apply in_app_or in Hin2. destruct Hin2 as [Hin2 | Hin2].
      - apply in_merge_branch_source_content in Hin2 as [s [Hins Hc]].
        rewrite in_app_iff in Hins.
        exists s. split; [ | apply Hc]. rewrite !in_app_iff. tauto.
      - exists e2. split; [ | reflexivity]. rewrite !in_app_iff. tauto. }
    destruct Hsrc1 as [s1 [Hins1 Hc1]].
    destruct Hsrc2 as [s2 [Hins2 Hc2]].
    assert (Heqid : event_id s1 = event_id s2).
    { rewrite <- (event_content_eq_id e1 s1 Hc1), <- (event_content_eq_id e2 s2 Hc2), Heq.
      reflexivity. }
    assert (Hs : s1 = s2)
      by (apply (all_same_id_equal_in_union3 b1 b2 b3 Hwf1 Hwf2 Hwf3 Hcompat s1 s2 Hins1 Hins2 Heqid)).
    subst s2.
    unfold event_content_eq in *. rewrite Hc1, Hc2. reflexivity.
Qed.

Lemma sort_dedup_content_eq_idem : forall b,
  well_formed b ->
  Forall2 event_content_eq
    (sort_by_id (dedup (b ++ b)))
    (sort_by_id (dedup (b ++ nil))).
Proof.
  intros b Hwf.
  apply eq_list_by_content.
  - rewrite !sort_by_id_preserves_ids, !dedup_preserves_ids, !ids_of_app. simpl.
    apply normalized_ids_eq_iff. intros n. rewrite !in_app_iff. firstorder.
  - apply distinct_ids_sort_dedup.
  - apply distinct_ids_sort_dedup.
  - intros e1 e2 Hin1 Hin2 Heq.
    rewrite in_sort_by_id in Hin1. apply in_dedup in Hin1.
    rewrite in_sort_by_id in Hin2. apply in_dedup in Hin2.
    simpl in Hin2.
    assert (Hin1' : In e1 b) by (rewrite in_app_iff in Hin1; tauto).
    assert (Hin2' : In e2 b)
      by (rewrite in_app_iff in Hin2; destruct Hin2 as [H | H]; [exact H | destruct H]).
    assert (e1 = e2) by (apply (distinct_ids_injective b (wf_distinct b Hwf) e1 e2 Hin1' Hin2' Heq)).
    subst. reflexivity.
Qed.

(* ------------------------------------------------------------------------- *)
(* Theorem 9 / CRDT properties.                                              *)
(* ------------------------------------------------------------------------- *)

Theorem merge_commutative : forall b1 b2 : branch,
  well_formed b1 -> well_formed b2 -> branch_compat b1 b2 ->
  merge_branch b1 b2 = merge_branch b2 b1.
Proof.
  intros b1 b2 Hwf1 Hwf2 Hcompat.
  unfold merge_branch. apply reanchor_aux_eq.
  apply sort_dedup_content_eq_comm; assumption.
Qed.

Theorem merge_associative : forall b1 b2 b3 : branch,
  well_formed b1 -> well_formed b2 -> well_formed b3 ->
  branches_compat3 b1 b2 b3 ->
  merge_branch b1 (merge_branch b2 b3) = merge_branch (merge_branch b1 b2) b3.
Proof.
  intros b1 b2 b3 Hwf1 Hwf2 Hwf3 Hcompat.
  unfold merge_branch. apply reanchor_aux_eq.
  apply sort_dedup_content_eq_assoc; assumption.
Qed.

Theorem merge_idempotent : forall b : branch,
  well_formed b ->
  merge_branch b b = merge_branch b nil.
Proof.
  intros b Hwf.
  unfold merge_branch. apply reanchor_aux_eq.
  apply sort_dedup_content_eq_idem; assumption.
Qed.

(* ------------------------------------------------------------------------- *)
(* Well-formedness preservation.                                             *)
(* ------------------------------------------------------------------------- *)

Lemma reanchor_aux_linkage : forall es prev_id,
  prev_linkage_aux (reanchor_aux es prev_id) prev_id.
Proof.
  induction es as [|e es' IH]; simpl; intros prev_id.
  - auto.
  - split; [reflexivity | apply IH].
Qed.

Lemma reanchor_linkage : forall es, axiom_prev_linkage (reanchor es).
Proof. intros es. apply reanchor_aux_linkage. Qed.

Lemma all_events_valid_merge : forall b1 b2,
  (forall e, In e b1 -> axiom_valid_event e) ->
  (forall e, In e b2 -> axiom_valid_event e) ->
  forall e, In e (merge_branch b1 b2) -> axiom_valid_event e.
Proof.
  intros b1 b2 Hv1 Hv2 e Hin.
  apply in_merge_branch_source_content in Hin as [s [Hins Hc]].
  apply event_content_eq_iff in Hc. destruct Hc as [Hid [Ha _]].
  apply in_app_or in Hins. destruct Hins as [H | H].
  - unfold axiom_valid_event. rewrite Ha. apply Hv1. apply H.
  - unfold axiom_valid_event. rewrite Ha. apply Hv2. apply H.
Qed.

Lemma increasing_ids_of_sorted_distinct : forall es,
  Sorted le (ids_of es) -> distinct_ids es -> axiom_increasing_ids es.
Proof.
  induction es as [|e es' IH]; simpl; intros Hsorted Hdist.
  - auto.
  - destruct es' as [|e2 es''].
    + auto.
    + split.
      * assert (Hle : event_id e <= event_id e2).
        { apply (Forall_forall (le (event_id e)) (ids_of (e2 :: es'')));
            [ apply (Sorted_extends Nat.le_trans Hsorted); left; auto | left; auto ]. }
        destruct Hdist as [Hneq _].
        assert (Hlt : event_id e < event_id e2 \/ event_id e = event_id e2) by lia.
        destruct Hlt as [Hlt | Heq']; auto.
        exfalso. apply Hneq with (e' := e2); auto. left; auto.
      * apply IH.
        -- inversion Hsorted; auto.
        -- destruct Hdist; auto.
Qed.

Lemma distinct_ids_merge : forall b1 b2, distinct_ids (merge_branch b1 b2).
Proof.
  intros b1 b2. apply distinct_ids_NoDup_ids_of.
  rewrite merge_branch_ids.
  apply Permutation_NoDup with (dedup_nat (ids_of b1 ++ ids_of b2)).
  - apply Permutation_sym. apply sort_nat_perm.
  - apply dedup_nat_nodup.
Qed.

Lemma increasing_ids_merge : forall b1 b2, axiom_increasing_ids (merge_branch b1 b2).
Proof.
  intros b1 b2.
  apply increasing_ids_of_sorted_distinct.
  - rewrite merge_branch_ids. apply normalized_ids_sorted.
  - apply distinct_ids_merge.
Qed.

Theorem merge_preserves_well_formed : forall b1 b2 : branch,
  well_formed b1 -> well_formed b2 -> well_formed (merge_branch b1 b2).
Proof.
  intros b1 b2 Hwf1 Hwf2.
  destruct Hwf1 as [Hv1 [Hd1 [Hi1 [Hp1 _]]]].
  destruct Hwf2 as [Hv2 [Hd2 [Hi2 [Hp2 _]]]].
  repeat split.
  - apply all_events_valid_merge; assumption.
  - apply distinct_ids_merge.
  - apply increasing_ids_merge.
  - apply reanchor_linkage.
  all: auto.
Qed.
