"use client"

import { useEffect } from "react"
import { zodResolver } from "@hookform/resolvers/zod"
import { createClientComponentClient } from "@supabase/auth-helpers-nextjs"
import { useForm } from "react-hook-form"
import { RxGithubLogo } from "react-icons/rx"
import * as z from "zod"

import { Api } from "@/lib/api"
import { analytics } from "@/lib/segment"
import { getSupabase } from "@/lib/supabase"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Spinner } from "@/components/ui/spinner"
import { Toaster } from "@/components/ui/toaster"
import { useToast } from "@/components/ui/use-toast"
import Logo from "@/components/logo"

const formSchema = z.object({
  email: z.string().email({
    message: "Invalid email address.",
  }),
})

const supabase = getSupabase()

export default function IndexPage() {
  const { toast } = useToast()
  const { ...form } = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      email: "",
    },
  })

  async function onSubmit(values: z.infer<typeof formSchema>) {
    const { email } = values
    const { error } = await supabase.auth.signInWithOtp({
      email,
    })

    if (error) {
      toast({
        description: `Ooops! ${error?.message}`,
      })

      return
    }

    toast({
      description: "🎉 Yay! Check your email for sign in link.",
    })
  }

  async function handleGithubLogin() {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "github",
    })

    if (error) {
      toast({
        description: `Ooops! ${error?.message}`,
      })

      return
    }
  }

  useEffect(() => {
    const { data: authListener } = supabase.auth.onAuthStateChange(
      (event, _session) => {
        if (event === "SIGNED_IN") {
          const fetchProfileAndIdentify = async () => {
            const { data: profile } = await supabase
              .from("profiles")
              .select("*")
              .eq("user_id", _session?.user.id)
              .single()
            if (profile.api_key) {
              const api = new Api(profile.api_key)
              await api.indentifyUser({
                anonymousId: (await analytics.user()).anonymousId(),
                email: _session?.user.email,
                firstName: profile.first_name,
                lastName: profile.last_name,
                company: profile.company,
              })
            }
            window.location.href = "/workflows"
          }
          fetchProfileAndIdentify()
        }
      }
    )

    return () => {
      authListener.subscription.unsubscribe()
    }
  }, [supabase.auth])

  return (
    <section className="container flex h-screen max-w-md flex-col justify-center space-y-8">
      <Logo width={50} height={50} />
      <Alert>
        <AlertTitle>Heads up!</AlertTitle>
        <AlertDescription>
          Use the authentication method you used the first time you signed up,
          either email or Github. Using both will result in duplicate accounts.
        </AlertDescription>
      </Alert>
      <div className="flex flex-col space-y-0">
        <p className="text-lg font-bold">Login to Superagent</p>
        <p className="text-sm text-muted-foreground">
          Enter your email to receive a one-time password
        </p>
      </div>
      <Form {...form}>
        <form
          onSubmit={form.handleSubmit(onSubmit)}
          className="w-full space-y-4"
        >
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormControl>
                  <Input placeholder="Enter your email" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
          <Button type="submit" size="sm" className="w-full">
            {form.control._formState.isSubmitting ? (
              <Spinner />
            ) : (
              "Send password"
            )}
          </Button>
        </form>
      </Form>
      <Separator />

      <Button
        variant="secondary"
        size="sm"
        className="space-x-4"
        onClick={handleGithubLogin}
      >
        <RxGithubLogo size={20} />
        <p>Sign in with GitHub</p>
      </Button>
      <Toaster />
    </section>
  )
}
