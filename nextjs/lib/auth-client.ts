import {createAuthClient} from "better-auth/react"

 const authClient = createAuthClient({
    
})

export const {signUp,signOut,signIn,useSession} = authClient