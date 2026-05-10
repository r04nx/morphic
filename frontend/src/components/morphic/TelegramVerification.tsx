import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { api } from "@/api/client";
import { toast } from "sonner";
import { Send, CheckCircle } from "lucide-react";

interface TelegramVerificationProps {
  username: string;
  onVerified: (chatId: string) => void;
  onCancel: () => void;
}

export function TelegramVerification({ username, onVerified, onCancel }: TelegramVerificationProps) {
  const [isSending, setIsSending] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [generatedCode, setGeneratedCode] = useState<string | null>(null);
  const [botUsername, setBotUsername] = useState<string | null>(null);
  const [isVerified, setIsVerified] = useState(false);

  const handleSendCode = async () => {
    if (!username) return;
    
    setIsSending(true);
    try {
      const result = await api.sendTelegramVerificationCode(username);
      if (result.success && result.verification_code) {
        setGeneratedCode(result.verification_code);
        setBotUsername(result.bot_username ?? null);
        toast.success("Verification code generated!");
      } else {
        toast.error(result.error || "Failed to send verification code");
      }
    } catch (error) {
      toast.error("Failed to send verification code");
    } finally {
      setIsSending(false);
    }
  };

  const handleVerifyCode = async () => {
    if (!generatedCode || !username) return;
    
    setIsVerifying(true);
    try {
      const result = await api.verifyTelegramChatId(username, generatedCode);
      if (result.success) {
        setIsVerified(true);
        toast.success("Telegram verified successfully!");
        setTimeout(() => {
          onVerified(result.chat_id || username);
        }, 1000);
      } else {
        toast.error(result.error || "Invalid verification code");
      }
    } catch (error) {
      toast.error("Verification failed");
    } finally {
      setIsVerifying(false);
    }
  };

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-blue-100 flex items-center justify-center">
            <Send className="h-4 w-4 text-blue-600" />
          </div>
          Verify Telegram
        </CardTitle>
        <CardDescription>
          Send a message to the bot from your Telegram account to link your chat
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!generatedCode ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Bot Username</Label>
              <div className="rounded-md border border-border bg-muted px-3 py-2 text-sm font-mono">@{username}</div>
            </div>
            <Button 
              onClick={handleSendCode} 
              disabled={isSending || !username}
              className="w-full"
            >
              {isSending ? "Sending..." : "Generate Code"}
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <Alert>
              <AlertDescription>
                <strong>Step 1:</strong> Open Telegram and send <strong>hi</strong> to <strong>@{botUsername || username}</strong>.
                <br />
                <strong>Step 2:</strong> Send this code to the same bot:
                <div className="mt-2 p-3 bg-muted rounded-md font-mono text-lg text-center">
                  {generatedCode}
                </div>
              </AlertDescription>
            </Alert>
            
            <div className="flex gap-2">
              <Button 
                onClick={handleVerifyCode} 
                disabled={isVerifying || isVerified}
                className="flex-1"
              >
                {isVerifying ? "Checking..." : "I Have Sent The Code"}
              </Button>
              <Button variant="outline" onClick={onCancel}>
                Cancel
              </Button>
            </div>
            
            {isVerified && (
              <Alert className="border-green-200 bg-green-50">
                <div className="flex items-center gap-2">
                  <CheckCircle className="h-4 w-4 text-green-600" />
                  <AlertDescription className="text-green-800">
                    Verification successful! Chat ID: <span className="font-mono">{result.chat_id || username}</span>. Test message sent via this chat ID.
                  </AlertDescription>
                </div>
              </Alert>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
