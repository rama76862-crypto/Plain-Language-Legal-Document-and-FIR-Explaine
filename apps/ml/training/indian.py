"""Small, explicitly synthetic Indian-context cue baseline, never legal validity.

Run: python -m apps.ml.training.indian --train
External JSONL may be supplied with --data; provenance and document families are
required. No account gates are bypassed and no test examples select thresholds.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import time
import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion
from sklearn.multiclass import OneVsRestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.metrics import f1_score, precision_recall_fscore_support
from apps.ml.service.contracts import ClassifierPrediction, ClassifierResult

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "training" / "indian_artifacts"
DATA = ROOT / "data" / "indian_cues.jsonl"
LABELS = ["payment_penalty","automatic_renewal","waived_rights","deposit_forfeiture","unilateral_change","unilateral_termination","limitation_of_liability"]
BASES = {
"payment_penalty": [
"The tenant must pay a late payment fee of INR {amount} if rent is received after the grace period.",
"The borrower owes a repayment penalty of {rate}% for overdue instalments.",
"A prepayment penalty of INR {amount} applies when this loan is paid before its stated term.",
"For each delayed rent payment the landlord may collect a charge of INR {amount}.",
"The customer incurs a penalty of {rate}% when an instalment is missed.",
"A late fee is charged on rent arrears at the rate stated in this agreement.",
"The lender imposes an additional payment charge when the borrower defaults on an instalment.",
"Missing the repayment date attracts an extra charge of INR {amount}.",
"A surcharge of {rate}% is payable if the monthly rent arrives after the allowed period."],
"automatic_renewal": [
"The tenancy renews automatically for another year unless written cancellation is received.",
"This agreement has automatic renewal at the end of its term.",
"The service subscription will auto-renew unless the customer opts out.",
"Unless the tenant sends a cancellation notice the lease is renewed automatically.",
"At expiry the agreement automatically continues for a further term.",
"The contract is subject to auto renewal and the notice period is stated separately.",
"The lease renews without a fresh signature if neither party sends notice.",
"The contract rolls over into a new term unless either party gives written notice.",
"The subscription continues for successive periods by default, without a new order."],
"waived_rights": [
"The tenant waives the right to claim a refund of the stated charge.",
"The borrower gives up the right to receive notice before the stated action.",
"The buyer surrenders the right to bring a claim concerning the listed defect.",
"The customer waives all rights to seek compensation under this clause.",
"The signatory agrees to waive any claim for a refund of the specified payment.",
"The tenant gives up the right to contest the deduction described here.",
"The borrower surrenders any right to challenge the listed account charge.",
"The buyer relinquishes any entitlement to compensation for the listed delay.",
"The tenant abandons the ability to dispute the specified deduction."],
"deposit_forfeiture": [
"The landlord may forfeit the entire security deposit if the tenant leaves early.",
"The tenant loses the deposit upon early termination of the lease.",
"The deposit is non-refundable when the stated cancellation condition applies.",
"The security amount shall be retained in full on the stated breach.",
"The landlord may deduct the whole deposit if this condition occurs.",
"The buyer forfeits the earnest money when the specified condition is breached.",
"The security deposit will not be returned following the stated default.",
"The advance is kept entirely by the owner if the booking is cancelled.",
"The paid security amount is lost if the occupant vacates before the stated date."],
"unilateral_change": [
"The lender may change the service fee without seeking the borrower's agreement.",
"The landlord can amend the rent clause by posting revised terms.",
"The provider reserves the right to vary charges at its sole discretion.",
"One party may modify these terms without agreement from the other party.",
"The company can alter this agreement by notifying the customer.",
"The owner may revise the listed charges without a new signed agreement.",
"The lender reserves a unilateral power to change the specified fee.",
"The provider alone can replace the listed conditions with revised wording.",
"The landlord has discretion to amend the payment terms without joint approval."],
"unilateral_termination": [
"The landlord may terminate this tenancy at its sole discretion.",
"The lender reserves the right to end this agreement without giving reasons.",
"The provider may cancel the contract whenever it chooses.",
"The owner may discontinue the agreement by issuing the stated notice.",
"The company alone may end the subscription under this clause.",
"The landlord reserves a unilateral termination right.",
"The lender may close the facility without a request from the borrower.",
"The provider can bring the arrangement to an end at its own election.",
"The owner alone can cancel this lease using the procedure stated here."],
"limitation_of_liability": [
"The provider is not liable for losses caused by the listed service failure.",
"The landlord limits liability to INR {amount} for the specified event.",
"The lender excludes liability for the stated indirect losses.",
"The company's liability shall not exceed the stated payment amount.",
"The seller accepts no responsibility for the specified consequential damage.",
"The provider caps compensation at the amount of the service charge.",
"The owner disclaims liability for the losses described in this clause.",
"Recovery from the supplier is restricted to INR {amount} for the listed loss.",
"The company will bear no responsibility for the particular damage described here."]
}
NORMAL = [
"The monthly rent is INR {amount} and the parties are named in the schedule.",
"The borrower will repay the principal in the instalments listed in the annexure.",
"No late payment fee or payment penalty applies under this clause.",
"The agreement does not renew automatically; a fresh signed agreement is required.",
"The tenant does not waive any rights or claims under this paragraph.",
"The security deposit is refundable after the agreed deductions are checked.",
"Both parties must agree in writing before changing the rent.",
"Either party may end the agreement using the same written notice procedure.",
"The buyer and seller identify the property by the khasra number in the schedule.",
"The notice records a request for documents within the stated period.",
"The contract ends on the listed expiry date and any extension requires fresh agreement.",
"This paragraph preserves the customer's ability to challenge account charges.",
"The tenant can recover the deposit after the documented inspection.",
"The parties jointly approve any amendment to the specified conditions."
]

def seed_data():
    rows = []
    for category, texts in [*BASES.items(), ("normal", NORMAL)]:
        for index, text in enumerate(texts):
            split = ("train" if index < 5 else "validation" if index < 7 else "test") if category != "normal" else ("train" if index < 8 else "validation" if index < 10 else "test")
            for variant in range(8 if split == "train" else 1):
                amount, rate = 500 + variant * 250, 1 + variant
                value = text.format(amount=amount,rate=rate)
                rows.append({"id":f"{category}-{index}-{variant}","family":f"{category}-{index}","split":split,"text":value,"labels":[] if category=="normal" else [category],"jurisdiction_context":"IN","source_type":"authored_synthetic","review_status":"not_independently_reviewed","license":"project-authored examples; no personal data","source_url":None})
    return rows

def load_rows(path: Path):
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    families = {}
    texts = {}
    for row in rows:
        if not row.get("family") or row.get("split") not in {"train","validation","test"} or not row.get("license"):
            raise ValueError("Each example requires family, split and licence")
        if set(row["labels"]) - set(LABELS):
            raise ValueError("Unknown attention label")
        if row.get("source_type") != "authored_synthetic" and (not row.get("source_url") or row.get("review_status") != "reviewed"):
            raise ValueError("External examples require a source locator and independent review")
        family = row["family"]
        if family in families and families[family] != row["split"]:
            raise ValueError("Document family crosses evaluation splits")
        families[family] = row["split"]
        normalized = " ".join(row["text"].casefold().split())
        if normalized in texts and texts[normalized] != row["split"]:
            raise ValueError("Exact normalized text overlaps evaluation splits")
        texts[normalized] = row["split"]
    return rows

def train(data: Path = DATA, output: Path = ARTIFACTS):
    started = time.perf_counter()
    rows = load_rows(data)
    sets = {split:[r for r in rows if r["split"]==split] for split in ("train","validation","test")}
    if any(not group for group in sets.values()):
        raise ValueError("All three data splits are required")
    encoder = MultiLabelBinarizer(classes=LABELS).fit([LABELS])
    vectorizer = FeatureUnion([("word",TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True)),("char",TfidfVectorizer(analyzer="char_wb",ngram_range=(3,5),sublinear_tf=True))])
    train_x = vectorizer.fit_transform([r["text"] for r in sets["train"]])
    estimator = OneVsRestClassifier(LogisticRegression(class_weight="balanced",max_iter=1000,random_state=17,solver="liblinear"))
    estimator.fit(train_x,encoder.transform([r["labels"] for r in sets["train"]]))
    fit_seconds = time.perf_counter()-started
    val_y = encoder.transform([r["labels"] for r in sets["validation"]])
    val_scores = estimator.predict_proba(vectorizer.transform([r["text"] for r in sets["validation"]]))
    thresholds = []
    for column in range(len(LABELS)):
        grid = np.arange(0.25,0.86,0.05)
        threshold = max(grid,key=lambda t:(f1_score(val_y[:,column],val_scores[:,column]>=t,zero_division=0),t))
        thresholds.append(float(threshold))
    # Exactly one held-out prediction pass. Do not tune using this report.
    test_y = encoder.transform([r["labels"] for r in sets["test"]])
    test_scores = estimator.predict_proba(vectorizer.transform([r["text"] for r in sets["test"]]))
    test_pred = test_scores >= np.array(thresholds)
    p,r,f,s = precision_recall_fscore_support(test_y,test_pred,average=None,zero_division=0)
    synthetic = all(row["source_type"]=="authored_synthetic" for row in rows)
    metrics = {"dataset_sha256":hashlib.sha256(data.read_bytes()).hexdigest(),"split_counts":{k:len(v) for k,v in sets.items()},"family_counts":{k:len({r["family"] for r in v}) for k,v in sets.items()},"fit_seconds":fit_seconds,"macro_f1":float(f1_score(test_y,test_pred,average="macro",zero_division=0)),"micro_f1":float(f1_score(test_y,test_pred,average="micro",zero_division=0)),"per_label":{label:{"precision":float(p[i]),"recall":float(r[i]),"f1":float(f[i]),"support":int(s[i])} for i,label in enumerate(LABELS)},"test_predictions":[{"id":row["id"],"truth":row["labels"],"predicted":[label for i,label in enumerate(LABELS) if test_pred[n,i]]} for n,row in enumerate(sets["test"])],"test_evaluation_count":1,"synthetic_only":synthetic,"independent_review":False if synthetic else all(row.get("review_status")=="reviewed" for row in rows),"limitations":["Small development benchmark, not Indian legal correctness.","Numeric variants share a family and are kept in one split.","Unreviewed synthetic annotations are not expert labels."]}
    output.mkdir(parents=True,exist_ok=True)
    joblib.dump({"vectorizer":vectorizer,"estimator":estimator,"thresholds":thresholds,"labels":LABELS},output/"classifier.joblib")
    metadata = {"classifier_version":"indian-context-cues-v1","training_source":"authored_synthetic_indian_context" if synthetic else "reviewed_external_examples","metrics":metrics}
    (output/"metadata.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    return metadata

class IndianClauseClassifier:
    def __init__(self, directory: Path = ARTIFACTS):
        payload = joblib.load(directory/"classifier.joblib")
        self.metadata = json.loads((directory/"metadata.json").read_text(encoding="utf-8"))
        self.version = self.metadata["classifier_version"]
        self.classifier_version = self.version
        self.vectorizer,self.estimator = payload["vectorizer"],payload["estimator"]
        self.thresholds,self.labels = payload["thresholds"],payload["labels"]
    def predict(self,text: str) -> ClassifierResult:
        scores = self.estimator.predict_proba(self.vectorizer.transform([text]))[0]
        return ClassifierResult(classifier_version=self.version,predictions=[ClassifierPrediction(label=label,score=float(score),threshold=threshold,detected=bool(score>=threshold)) for label,score,threshold in zip(self.labels,scores,self.thresholds)])

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--train",action="store_true")
    parser.add_argument("--data",type=Path,default=DATA)
    parser.add_argument("--seed",action="store_true")
    args=parser.parse_args()
    if args.seed:
        args.data.parent.mkdir(parents=True,exist_ok=True)
        if args.data.exists():
            raise SystemExit("Refusing to overwrite an existing dataset")
        args.data.write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in seed_data()),encoding="utf-8")
    if args.train:
        report=train(args.data)
        print(json.dumps({k:v for k,v in report["metrics"].items() if k!="test_predictions"},indent=2))

if __name__=="__main__":
    main()

