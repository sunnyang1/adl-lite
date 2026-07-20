(* Event.v -- ADL Lite event model.
   Events are the atoms of an EventChain; status/confidence are derived. *)

Require Import List String.
Require Import ADL.Status ADL.Crypto.

Inductive adl_event_type : Set :=
  | REGISTER
  | VALIDATE
  | DEPRECATE
  | FORK
  | ARCHIVE
  | RELATE
  | EVIDENCE
  | SEAL
  | ANNOUNCE
  | SNAPSHOT.

Record event : Set := mkEvent {
  event_id      : nat;
  actor         : string;
  event_type    : adl_event_type;
  confidence    : nat;
  prev          : option nat;
  (* Cryptographic fields.  [None] means the event is unsigned (e.g. a
     synthetic event reconstructed from YAML front matter). *)
  signature     : option sig_bytes;
  public_key    : option pubkey
}.

(* Default event used for [nth] fallbacks. *)
Definition default_event : event :=
  mkEvent 0 EmptyString REGISTER 0 None None None.

(* StatusOf maps each event type to its derived status. *)
Definition StatusOf (et : adl_event_type) : status :=
  match et with
  | REGISTER   => PROVISIONAL
  | VALIDATE   => VALIDATED
  | DEPRECATE  => DEPRECATED
  | FORK       => FORKED
  | ARCHIVE    => ARCHIVED
  | RELATE     => PROVISIONAL
  | EVIDENCE   => PROVISIONAL
  | SEAL       => PROVISIONAL
  | ANNOUNCE   => PROVISIONAL
  | SNAPSHOT   => PROVISIONAL
  end.

(* Lemma: VALIDATED is only produced by the VALIDATE event type. *)
Lemma StatusOf_eq_VALIDATED : forall (et : adl_event_type),
  StatusOf et = VALIDATED <-> et = VALIDATE.
Proof.
  intros et. split.
  - destruct et; simpl; try discriminate; auto.
  - intros H. rewrite H. simpl. reflexivity.
Qed.
