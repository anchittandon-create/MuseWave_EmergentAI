import { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";
import { UserCog, Save, Trash2 } from "lucide-react";
import { API } from "../App";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

export default function AccountSettingsPage({ user, onUserUpdated, onAccountDeleted }) {
  const [formData, setFormData] = useState({ name: "", mobile: "" });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    setFormData({
      name: user?.name || "",
      mobile: user?.mobile || user?.phoneNumber || "",
    });
  }, [user]);

  const saveProfile = async () => {
    if (!user?.id) return;
    if (!formData.name.trim()) {
      toast.error("Name is required");
      return;
    }
    if (!formData.mobile.trim()) {
      toast.error("Phone number is required");
      return;
    }

    try {
      setSaving(true);
      const res = await axios.patch(`${API}/users/${user.id}`, {
        name: formData.name.trim(),
        mobile: formData.mobile.trim(),
        phoneNumber: formData.mobile.trim(),
      });
      onUserUpdated?.(res.data);
      toast.success("Profile updated");
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  const deleteAccount = async () => {
    if (!user?.id) return;
    const confirmed = window.confirm(
      "Delete your account and all songs/albums permanently? This cannot be undone."
    );
    if (!confirmed) return;

    try {
      setDeleting(true);
      await axios.delete(`${API}/users/${user.id}`);
      toast.success("Account deleted");
      onAccountDeleted?.();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to delete account");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="min-h-screen p-6 lg:p-10" data-testid="account-settings-page">
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h1 className="font-display text-3xl lg:text-4xl font-bold tracking-tight mb-2 flex items-center gap-3">
            <UserCog className="w-8 h-8 text-primary" />
            Account Settings
          </h1>
          <p className="text-muted-foreground">Manage your profile and account ownership.</p>
        </div>

        <div className="glass rounded-2xl p-6 space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-wide text-muted-foreground">Name</Label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="Your name"
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-wide text-muted-foreground">Phone Number</Label>
              <Input
                value={formData.mobile}
                onChange={(e) => setFormData((prev) => ({ ...prev, mobile: e.target.value }))}
                placeholder="Your phone number"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">User ID</p>
              <p className="font-mono text-xs break-all">{user?.id || "-"}</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-muted-foreground mb-1">Role</p>
              <p>{user?.role || "User"}</p>
            </div>
          </div>

          <Button onClick={saveProfile} disabled={saving} className="gap-2">
            <Save className="w-4 h-4" />
            {saving ? "Saving..." : "Save Profile"}
          </Button>
        </div>

        <div className="glass rounded-2xl p-6 space-y-4 border border-destructive/30">
          <h2 className="text-lg font-semibold">Danger Zone</h2>
          <p className="text-sm text-muted-foreground">
            Deleting your account removes all your songs, albums, and related records.
          </p>
          <Button
            variant="destructive"
            onClick={deleteAccount}
            disabled={deleting}
            className="gap-2"
          >
            <Trash2 className="w-4 h-4" />
            {deleting ? "Deleting..." : "Delete Account"}
          </Button>
        </div>
      </div>
    </div>
  );
}

export { AccountSettingsPage };
