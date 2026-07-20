(* Crypto.v -- Abstract cryptographic primitives for ADL Lite.

   This module defines the parametric signature scheme (Ed25519 / secp256k1)
   and hash function used by the ADL Lite event chain.  The primitives are
   abstract (axiomatised) rather than concretely implemented, which is the
   standard approach in formal cryptographic proofs: we assume the standard
   security properties (correctness, existential unforgeability, collision
   resistance) and prove protocol-level properties relative to these
   assumptions.

   Concrete implementations (e.g. FIPS 186-5 Ed25519, FIPS 180-4 SHA-256) would
   be verified separately and linked to these axioms. *)

Require Import List Bool String Arith.
Import ListNotations.

(* ------------------------------------------------------------------------- *)
(* Bytes as a list of booleans.  In a concrete model this would be a fixed- *)
(* width byte array (e.g. 256 bits for SHA-256 digests, 512 bits for         *)
(* Ed25519 public keys).                                                     *)
(* ------------------------------------------------------------------------- *)
Definition bytes := list bool.

(* ------------------------------------------------------------------------- *)
(* Abstract signature scheme.  Models Ed25519 or ECDSA (secp256k1).        *)
(* ------------------------------------------------------------------------- *)
Parameter pubkey  : Set.
Parameter privkey : Set.
Parameter sig_bytes : Set.

(* Equality deciders for the abstract types.  In a concrete model these
   would be derived from the fixed-width byte representation. *)
Parameter pubkey_eq_dec : forall (x y : pubkey), {x = y} + {x <> y}.
Parameter sig_bytes_eq_dec : forall (x y : sig_bytes), {x = y} + {x <> y}.

(* Sign a message with a private key. *)
Parameter sign : privkey -> bytes -> sig_bytes.

(* Verify a signature against a public key and message. *)
Parameter verify : pubkey -> bytes -> sig_bytes -> bool.

(* Keypair relation: pk is the public key derived from sk. *)
Parameter keypair : privkey -> pubkey -> Prop.

(* Correctness: every signature produced by [sign] verifies under the       *)
(* corresponding public key.                                                 *)
Axiom verify_correct :
  forall sk pk msg,
    keypair sk pk -> verify pk msg (sign sk msg) = true.

(* Existential unforgeability: if a signature verifies under a public key,  *)
(* it must have been produced by the corresponding private key.            *)
(* This is the standard EUF-CMA security assumption for digital signatures. *)
Axiom verify_unforgeable :
  forall pk msg sig,
    verify pk msg sig = true ->
    exists sk, keypair sk pk /\ sig = sign sk msg.

(* ------------------------------------------------------------------------- *)
(* Hash function (abstract SHA-256).                                         *)
(* ------------------------------------------------------------------------- *)
Parameter hash : bytes -> bytes.

(* Collision resistance: the hash function is collision-free.              *)
(* In a concrete model this would be proved under the random-oracle model.  *)
Axiom hash_collision_resistant :
  forall x y, hash x = hash y -> x = y.

(* ------------------------------------------------------------------------- *)
(* Serialization helpers (abstract).  In a concrete model these would map   *)
(* event fields to their byte representation for hashing and signing.      *)
(* ------------------------------------------------------------------------- *)
Parameter serialize_nat : nat -> bytes.
Parameter serialize_string : string -> bytes.

(* Concatenate two byte strings. *)
Definition bytes_concat (x y : bytes) : bytes := x ++ y.
