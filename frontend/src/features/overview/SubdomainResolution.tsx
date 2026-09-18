import { useMutation } from '@tanstack/react-query'
import { resolveSubdomains } from '../../api/overview'

interface SubdomainResolutionProps {
  uploadId: string
  firstPartyRoot: string
  subdomains: string[]
}

/** Opt-in DNS + WHOIS report: follows each subdomain's CNAME chain to an IP,
 * then looks up who WHOIS/RDAP says owns it. Slow and network-bound, so it
 * only runs on an explicit click -- never automatically. */
export function SubdomainResolution({ uploadId, firstPartyRoot, subdomains }: SubdomainResolutionProps) {
  const mutation = useMutation({
    mutationFn: () => resolveSubdomains(uploadId, subdomains),
  })

  return (
    <div>
      <h4>DNS Resolution for `{firstPartyRoot}` Subdomains</h4>
      <p className="overview__caption">
        Fully resolves each subdomain -- following any CNAME chain, the way <code>dig</code> would -- down to an IP
        address, then looks up who WHOIS/RDAP says owns that IP.
      </p>
      <button onClick={() => mutation.mutate()} disabled={mutation.isPending}>
        {mutation.isPending ? `Resolving ${subdomains.length} subdomain(s)...` : 'Resolve subdomains'}
      </button>

      {mutation.isError && <p className="overview__error">Failed to resolve subdomains.</p>}

      {mutation.data && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Subdomain</th>
              <th>Resolution Chain</th>
              <th>IP Address(es)</th>
              <th>WHOIS Organization</th>
            </tr>
          </thead>
          <tbody>
            {mutation.data.map((row) => (
              <tr key={row.subdomain}>
                <td>{row.subdomain}</td>
                <td>{row.chain}</td>
                <td>{row.ips}</td>
                <td>{row.organization}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
